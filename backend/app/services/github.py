from __future__ import annotations

import asyncio
import base64
import logging
import time
from collections import defaultdict
from typing import Any

import httpx

from app import config

logger = logging.getLogger(__name__)

GITHUB_SEARCH = "https://api.github.com/search/code"
GITHUB_REPOS = "https://api.github.com/repos"
DEFAULT_HEADERS: dict[str, str] = {
    "Accept": "application/vnd.github+json",
    f"X-GitHub-Api-Version": config.GITHUB_API_VERSION,
}


def _github_headers() -> dict[str, str]:
    h = {**DEFAULT_HEADERS, "User-Agent": "CodeLens/1.0"}
    if config.GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return h


def _backoff_from_response(response: httpx.Response) -> int:
    rem = response.headers.get("X-RateLimit-Remaining")
    if rem is not None and int(rem) > 0:
        return 0
    reset = int(response.headers.get("X-RateLimit-Reset") or 0)
    now = int(time.time())
    return min(max(0, reset - now) + 1, 60)


async def _backoff_for_rate_limit(client: httpx.AsyncClient) -> None:
    r = await client.get(
        "https://api.github.com/rate_limit", headers=_github_headers(), timeout=30.0
    )
    if r.status_code != 200:
        await asyncio.sleep(15)
        return
    j = r.json()
    for key in ("search", "core"):
        rsrc = (j.get("resources") or {}).get(key) or {}
        if rsrc.get("remaining", 1) == 0:
            reset = int(rsrc.get("reset", 0) or 0)
            w = min(max(0, reset - int(time.time())) + 1, 60)
            logger.warning("GitHub %s rate limit; sleeping %s s", key, w)
            await asyncio.sleep(w)
            return


def _select_hits(
    all_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_repo: dict[str, list[dict[str, Any]]] = {}
    for item in all_items:
        repo = item.get("repository") or {}
        rname = str(repo.get("full_name", ""))
        if not rname:
            continue
        if rname not in by_repo and len(by_repo) >= config.SEARCH_MAX_REPOS:
            continue
        if rname not in by_repo:
            by_repo[rname] = []
        if len(by_repo[rname]) >= config.SEARCH_MAX_FILES_PER_REPO:
            continue
        by_repo[rname].append(item)
    out: list[dict[str, Any]] = []
    for _rn, ar in by_repo.items():
        out.extend(ar)
    return out


async def _fetch_file_content(
    client: httpx.AsyncClient, api_url: str, headers: dict[str, str]
) -> str:
    w = 0
    for attempt in range(3):
        if w:
            await asyncio.sleep(w)
        r = await client.get(api_url, headers=headers, timeout=60.0)
        w = _backoff_from_response(r)
        if w and r.status_code not in (200, 404) and attempt < 2:
            continue
        if r.status_code != 200:
            return ""
        data = r.json()
        if data.get("encoding") == "base64" and data.get("content") is not None:
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return ""
    return ""

async def _fetch_repo_meta(
    client: httpx.AsyncClient, full_name: str, headers: dict[str, str]
) -> dict[str, Any]:
    w = 0
    for attempt in range(3):
        if w:
            await asyncio.sleep(w)
        r = await client.get(f"{GITHUB_REPOS}/{full_name}", headers=headers, timeout=30.0)
        w = _backoff_from_response(r)
        if w and r.status_code not in (200, 404) and attempt < 2:
            continue
        if r.status_code == 200:
            data = r.json()
            return {
                "stars": int(data.get("stargazers_count", 0)),
                "pushed_at": str(data.get("pushed_at") or ""),
                "archived": bool(data.get("archived", False)),
                "open_issues": int(data.get("open_issues_count", 0)),
            }
        break
    return {"stars": 0, "pushed_at": "", "archived": False, "open_issues": 0}


async def search_code(query: str) -> list[dict[str, Any]]:
    if not config.GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN is not set")

    headers = _github_headers()
    all_items: list[dict[str, Any]] = []
    total_in_index = 10_000_000

    async with httpx.AsyncClient() as client:
        for page in range(1, 4):
            if (page - 1) * 100 >= total_in_index:
                break
            w = 0
            for attempt in range(4):
                if w:
                    await asyncio.sleep(w)
                r = await client.get(
                    GITHUB_SEARCH,
                    params={"q": query, "per_page": 100, "page": page},
                    headers=headers,
                    timeout=60.0,
                )
                w = _backoff_from_response(r)
                if r.status_code in (403, 429) or "rate limit" in (r.text or "").lower():
                    await _backoff_for_rate_limit(client)
                    w = 0
                    if attempt < 3:
                        continue
                if r.status_code == 422:
                    r.raise_for_status()
                r.raise_for_status()
                j = r.json()
                if page == 1:
                    total_in_index = int(j.get("total_count", 0) or 0)
                break

            items = j.get("items") or []
            if not items:
                break
            all_items.extend(items)

    selected = _select_hits(all_items)
    if not selected:
        return []

    seen_repos = {str((i.get("repository") or {}).get("full_name", "")) for i in selected}
    seen_repos.discard("")

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        h = _github_headers()
        meta_by_repo: dict[str, dict] = {}
        for rname in seen_repos:
            meta_by_repo[rname] = await _fetch_repo_meta(client, rname, h)
        for item in selected:
            api_url = item.get("url") or ""
            if not api_url:
                continue
            repo = item.get("repository") or {}
            rname = str(repo.get("full_name", ""))
            meta = meta_by_repo.get(rname, {"stars": 0, "pushed_at": "", "archived": False, "open_issues": 0})  # <- estava faltando
            raw = await _fetch_file_content(client, api_url, h)
            results.append({
                "repo_full_name": rname,
                "repo_url": str(repo.get("html_url", "") or f"https://github.com/{rname}"),  # <- estava com ...
                "repo_stars": meta.get("stars", 0),
                "repo_pushed_at": meta.get("pushed_at", ""),
                "repo_archived": meta.get("archived", False),
                "repo_open_issues": meta.get("open_issues", 0),
                "file_path": str(item.get("path", "")),  # <- estava com ...
                "raw_content": raw,
            })

    return results

async def search_code_hybrid(subproblem) -> list[dict[str, Any]]:
    """
    Busca semântica (query principal) + busca estrutural (padrões de código).
    As structural_queries encontram repos relevantes mesmo sem README descritivo.
    Deduplica por (repo, arquivo) e respeita SEARCH_MAX_REPOS.
    """
    all_queries = [subproblem.query] + (subproblem.structural_queries or [])[:2]

    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, Any]] = []

    for query in all_queries:
        try:
            results = await search_code(query)
        except Exception as exc:
            logger.warning("structural query '%s' failed: %s", query, exc)
            continue
        for r in results:
            key = (r["repo_full_name"], r["file_path"])
            if key not in seen:
                seen.add(key)
                merged.append(r)

    # Re-aplica o limite de repos distintos sobre o resultado combinado
    by_repo: dict[str, list] = {}
    for r in merged:
        rn = r["repo_full_name"]
        if rn not in by_repo and len(by_repo) >= config.SEARCH_MAX_REPOS:
            continue
        by_repo.setdefault(rn, []).append(r)

    return [r for items in by_repo.values() for r in items]