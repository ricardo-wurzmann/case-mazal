from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    FileExtract,
    ProjectRequest,
    SearchStats,
    SubproblemInfo,
)
from app.services import extractor, scorer
from app.services.decomposer import DecompositionResult, Subproblem, decompose_idea
from app.services.github import search_code
from app.services.synthesizer import stream_synthesis

logger = logging.getLogger(__name__)

router = APIRouter()

SCORER_TOP_N = 30
SYNTHESIS_TOP_PER_SUBPROBLEM = 5
STATS_TOP_REPOS = 5


async def _search_subproblem(
    subproblem: Subproblem,
) -> tuple[Subproblem, list[FileExtract]]:
    try:
        raw_files = await search_code(subproblem.query)
    except Exception:
        logger.exception("Search failed for subproblem '%s'", subproblem.name)
        return subproblem, []

    if not raw_files:
        return subproblem, []

    extracts = [extractor.extract_usage(f, subproblem.query) for f in raw_files]
    for e in extracts:
        e.subproblem = subproblem.name

    ranked = scorer.score_and_filter(extracts, top_n=SCORER_TOP_N)
    return subproblem, ranked


async def _run_project_pipeline(
    idea: str,
) -> tuple[DecompositionResult, dict[str, list[FileExtract]], SearchStats]:

    decomposition = await decompose_idea(idea)

    results = await asyncio.gather(
        *[_search_subproblem(sp) for sp in decomposition.subproblems]
    )

    extracts_by_subproblem: dict[str, list[FileExtract]] = {}
    all_extracts: list[FileExtract] = []

    subproblem_infos: list[SubproblemInfo] = []
    for subproblem, extracts in results:
        extracts_by_subproblem[subproblem.name] = extracts
        all_extracts.extend(extracts)
        repos = {e.repo_name for e in extracts}
        subproblem_infos.append(
            SubproblemInfo(
                name=subproblem.name,
                description=subproblem.description,
                query=subproblem.query,
                repos_found=len(repos),
                files_found=len(extracts),
            )
        )

    all_ranked = scorer.score_and_filter(all_extracts, top_n=100)

    lang_counter: Counter[str] = Counter(e.language for e in all_ranked)
    repo_counter: Counter[str] = Counter(e.repo_name for e in all_ranked)
    top_repos = [r for r, _ in repo_counter.most_common(STATS_TOP_REPOS)]
    top_scores = [e.total_score for e in all_ranked[:20]]
    min_top = round(min(top_scores), 3) if top_scores else 0.0

    stats = SearchStats(
        total_repos=len(repo_counter),
        total_files=len(all_ranked),
        languages=dict(lang_counter),
        top_repos=top_repos,
        min_top_score=min_top,
        subproblems=subproblem_infos,
        detected_language=decomposition.language,
    )

    return decomposition, extracts_by_subproblem, stats


@router.post("/project/stream")
async def project_stream(body: ProjectRequest) -> StreamingResponse:

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'status', 'data': 'Decomposing your idea into subproblems...'})}\n\n"

            try:
                decomposition, extracts_by_subproblem, stats = await _run_project_pipeline(body.idea)
            except RuntimeError as exc:
                yield f"data: {json.dumps({'type': 'error', 'data': str(exc)})}\n\n"
                return
            except Exception as exc:
                logger.exception("Pipeline failed")
                yield f"data: {json.dumps({'type': 'error', 'data': 'Pipeline failed: ' + str(exc)})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'decomposition', 'data': [{'name': sp.name, 'description': sp.description, 'query': sp.query} for sp in decomposition.subproblems]})}\n\n"
            yield f"data: {json.dumps({'type': 'stats', 'data': stats.model_dump()})}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'data': 'Synthesizing architecture and reuse strategy...'})}\n\n"

            total_found = sum(len(v) for v in extracts_by_subproblem.values())
            if total_found == 0:
                yield f"data: {json.dumps({'type': 'error', 'data': 'No code found for this idea. Try describing it differently.'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            top_by_subproblem: dict[str, list[FileExtract]] = {
                sp_name: extracts[:SYNTHESIS_TOP_PER_SUBPROBLEM]
                for sp_name, extracts in extracts_by_subproblem.items()
            }

            try:
                async for token in stream_synthesis(
                    body.idea,
                    decomposition.language,
                    decomposition.subproblems,
                    top_by_subproblem,
                ):
                    yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"
            except Exception:
                logger.exception("Synthesis streaming failed")
                yield f"data: {json.dumps({'type': 'error', 'data': 'Synthesis unavailable — stats are still shown.'})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception:
            logger.exception("Unexpected error in event_generator")
            yield f"data: {json.dumps({'type': 'error', 'data': 'Unexpected server error.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")