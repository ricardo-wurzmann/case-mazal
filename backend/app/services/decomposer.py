from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import httpx

from app import config

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

LANGUAGE_EXTENSIONS: dict[str, str] = {
    "python": "py",
    "javascript": "js",
    "typescript": "ts",
    "go": "go",
    "rust": "rs",
    "java": "java",
    "ruby": "rb",
    "php": "php",
    "csharp": "cs",
    "c#": "cs",
    "cpp": "cpp",
    "c++": "cpp",
    "swift": "swift",
    "kotlin": "kt",
    "scala": "scala",
}

DECOMPOSE_SYSTEM = """You are a senior software architect. 
Your job is to decompose a project idea into concrete technical subproblems and generate optimized GitHub code search queries for each one.
You must respond ONLY with a valid JSON object — no markdown, no explanation, no backticks."""

DECOMPOSE_USER = """Project idea: "{idea}"

Analyze this project and respond with a JSON object in exactly this format:
{{
  "language": "python",
  "extension": "py",
  "subproblems": [
    {{
      "name": "short name of subproblem",
      "description": "what this subproblem solves",
      "query": "optimized github code search query extension:py"
    }}
  ]
}}

Rules:
- Detect the programming language from the idea. If none is mentioned, default to python/py.
- Generate 3 to 5 subproblems that together cover the full project.
- Each query must be specific enough to find real code (not docs), include the extension filter, and use 2-4 keywords max.
- Queries must target actual implementation code, not setup or configuration.
- Example queries: "whisper transcribe audio extension:py", "yt-dlp download video extension:py", "ffmpeg extract audio subprocess extension:py"
- Respond ONLY with the JSON object."""


@dataclass
class Subproblem:
    name: str
    description: str
    query: str


@dataclass
class DecompositionResult:
    language: str
    extension: str
    subproblems: list[Subproblem]


async def decompose_idea(idea: str) -> DecompositionResult:
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    payload = {
        "model": config.OPENROUTER_MODEL,
        "max_tokens": 800,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": DECOMPOSE_SYSTEM},
            {"role": "user", "content": DECOMPOSE_USER.format(idea=idea)},
        ],
    }

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "CodeLens",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(OPENROUTER_URL, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()

    raw = data["choices"][0]["message"]["content"].strip()

    # strip markdown fences if model wraps in ```json
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    parsed = json.loads(raw)

    language = str(parsed.get("language", "python")).lower()
    extension = str(parsed.get("extension", LANGUAGE_EXTENSIONS.get(language, "py")))

    subproblems = [
        Subproblem(
            name=str(sp.get("name", "")),
            description=str(sp.get("description", "")),
            query=str(sp.get("query", "")),
        )
        for sp in parsed.get("subproblems", [])
        if sp.get("query")
    ]

    if not subproblems:
        raise ValueError("LLM returned no subproblems")

    logger.info(
        "Decomposed '%s' into %d subproblems (language=%s)",
        idea[:60],
        len(subproblems),
        language,
    )

    return DecompositionResult(
        language=language,
        extension=extension,
        subproblems=subproblems,
    )