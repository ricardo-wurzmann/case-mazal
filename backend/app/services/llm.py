from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

from app import config
from app.models.schemas import FileExtract

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are a senior software engineer analyzing how a specific library, tool, or pattern "
    "is used across many real-world codebases. "
    "You have been given pre-filtered code snippets from GitHub repositories. "
    "Your job is to synthesize this into a clear, developer-friendly analysis."
)


def _format_extracts(extracts: list[FileExtract]) -> str:
    parts: list[str] = []
    for i, e in enumerate(extracts, 1):
        imports_str = "\n  ".join(e.imports) if e.imports else "(none detected)"
        snippets_str = "\n---snippet---\n".join(e.usage_snippets) if e.usage_snippets else "(none)"
        parts.append(
            f"[{i}] Repository: {e.repo_name}\n"
            f"    Language:   {e.language}\n"
            f"    File:       {e.file_path}\n"
            f"    Imports found:\n  {imports_str}\n"
            f"    Usage snippets:\n{snippets_str}"
        )
    return "\n\n".join(parts)


def _build_user_prompt(query: str, extracts: list[FileExtract]) -> str:
    n_files = len(extracts)
    repos = {e.repo_name for e in extracts}
    n_repos = len(repos)
    formatted = _format_extracts(extracts)

    return (
        f'Query: "{query}"\n\n'
        f"Here are {n_files} code extracts from {n_repos} repositories showing real usage:\n\n"
        f"{formatted}\n\n"
        "Please analyze and respond with:\n"
        "1. **Overview**: What is this typically used for based on the code found?\n"
        "2. **Most common import patterns**: How is it imported across different languages?\n"
        "3. **Most common usage patterns**: What are the most frequent ways it's called or used?\n"
        "4. **Variations found**: What are the different approaches seen?\n"
        "5. **Notable examples**: Highlight 2-3 particularly interesting or clean usage examples "
        "with the repo name.\n"
        "6. **Summary**: One paragraph summarizing the most practical way to use this based on "
        "real code evidence."
    )


async def analyze_with_llm(query: str, extracts: list[FileExtract]) -> str:
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    payload = {
        "model": config.OPENROUTER_MODEL,
        "max_tokens": 1500,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(query, extracts)},
        ],
    }

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "CodeLens",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(OPENROUTER_URL, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()

    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError) as exc:
        logger.error("Unexpected OpenRouter response: %s", data)
        raise RuntimeError("Unexpected response from OpenRouter") from exc


async def stream_analysis(query: str, extracts: list[FileExtract]) -> AsyncIterator[str]:
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    payload = {
        "model": config.OPENROUTER_MODEL,
        "max_tokens": 1500,
        "temperature": 0.3,
        "stream": True,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(query, extracts)},
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
            # r.raise_for_status()
            if r.status_code != 200:
                body = await r.aread()
                logger.error("OpenRouter error %s: %s", r.status_code, body.decode())
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