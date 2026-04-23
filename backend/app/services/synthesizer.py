from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

from app import config
from app.models.schemas import FileExtract
from app.services.decomposer import Subproblem

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYNTHESIS_SYSTEM = """You are a senior software engineer doing a code research report.
You have real code extracts from GitHub repositories for each subproblem of a project.
Your job is to produce a CONCISE, PRACTICAL blueprint — focused on HOW to use each library/technique, not on writing complete files.

STRICT RULES:
- For each subproblem: show ONE short usage snippet (5-15 lines max) from the best extract found, or a minimal example if no extract was found
- Never write complete classes or full implementations
- Never repeat the same code twice
- Keep each section SHORT — the goal is a developer reading this in 2 minutes and knowing exactly what to do
- Be direct, no filler text"""


def _format_subproblem_extracts(
    subproblem: Subproblem,
    extracts: list[FileExtract],
) -> str:
    lines = [
        f"### Subproblem: {subproblem.name}",
        f"Goal: {subproblem.description}",
        f"Extracts found: {len(extracts)}",
        "",
    ]
    for i, e in enumerate(extracts[:3], 1):
        imports_str = ", ".join(e.imports[:3]) if e.imports else "(none)"
        snippet = e.usage_snippets[0] if e.usage_snippets else "(no snippet)"
        lines += [
            f"[{i}] {e.repo_name} — {e.file_path} (score: {e.total_score:.2f})",
            f"    Imports: {imports_str}",
            f"    Code snippet:",
            *[f"    {line}" for line in snippet.splitlines()[:10]],
            "",
        ]
    return "\n".join(lines)


def _build_synthesis_prompt(
    idea: str,
    language: str,
    subproblems: list[Subproblem],
    extracts_by_subproblem: dict[str, list[FileExtract]],
) -> str:
    sections = [
        f'Project idea: "{idea}"',
        f"Primary language: {language}",
        "",
        "## Real code extracts found per subproblem (from GitHub):",
        "",
    ]

    for sp in subproblems:
        extracts = extracts_by_subproblem.get(sp.name, [])
        sections.append(_format_subproblem_extracts(sp, extracts))

    sections += [
        "",
        "## Your output must follow EXACTLY this structure (keep each section brief):",
        "",
        "### 1. Overview",
        "2-3 sentences on what this project does and the main technical approach.",
        "",
        "### 2. Subproblem Breakdown",
        "For EACH subproblem:",
        "- Status: ✅ (code found) or ⚠️ (no extract, use standard library)",
        "- Best source repo (if found)",
        "- ONE short usage snippet (5-15 lines) showing HOW to use the library/technique",
        "- One line on what to adapt",
        "",
        "### 3. Integration Sketch",
        "A single short pseudocode block (10-20 lines max) showing the main pipeline flow connecting all subproblems. No full implementations.",
        "",
        "### 4. What to Write from Scratch",
        "A simple table: | Subproblem | Status | Notes |",
        "",
        "### 5. Recommended Dependencies",
        "pip install commands only. No explanations.",
        "",
        "### 6. Summary",
        "3-4 sentences. Estimated lines of new code needed. Key insight from the research.",
    ]

    return "\n".join(sections)


async def stream_synthesis(
    idea: str,
    language: str,
    subproblems: list[Subproblem],
    extracts_by_subproblem: dict[str, list[FileExtract]],
) -> AsyncIterator[str]:
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    user_prompt = _build_synthesis_prompt(idea, language, subproblems, extracts_by_subproblem)

    payload = {
        "model": config.OPENROUTER_MODEL,
        "max_tokens": 1500,
        "temperature": 0.2,
        "stream": True,
        "messages": [
            {"role": "system", "content": SYNTHESIS_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
    }

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "CodeLens",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", OPENROUTER_URL, json=payload, headers=headers) as r:
            if r.status_code != 200:
                body = await r.aread()
                logger.error("OpenRouter synthesis error %s: %s", r.status_code, body.decode())
                r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = line[len("data:"):].strip()
                if chunk == "[DONE]":
                    break
                try:
                    data = json.loads(chunk)
                    delta = data["choices"][0]["delta"].get("content") or ""
                    if delta:
                        yield delta
                except Exception:
                    continue