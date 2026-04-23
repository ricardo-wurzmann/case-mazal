from __future__ import annotations

import re
from typing import Any

from app import config
from app.models.schemas import FileExtract

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".cc": "C++",
    ".h": "C++",
    ".c": "C",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".r": "R",
    ".sh": "Shell",
    ".bash": "Shell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".json": "JSON",
}


def _detect_language(file_path: str) -> str:
    lower = file_path.lower()
    for ext, lang in EXTENSION_TO_LANGUAGE.items():
        if lower.endswith(ext):
            return lang
    return "Unknown"


def _location_score(file_path: str) -> float:
    parts = file_path.lower().replace("\\", "/").split("/")
    for part in parts:
        if part in ("src", "lib", "core", "internal", "pkg"):
            return 1.0
        if part in ("example", "examples", "demo", "demos", "sample", "samples"):
            return 0.8
        if part in ("test", "tests", "spec", "specs", "__tests__", "testing"):
            return 0.5
        if part in ("docs", "doc", "documentation"):
            return 0.3
    if "/" not in file_path.strip("/"):
        return 0.9
    return 0.6


def _extract_imports(lines: list[str], query_term: str, language: str) -> list[str]:
    found: list[str] = []
    term = re.escape(query_term.split()[0])

    if language == "Python":
        patterns = [
            rf"^\s*import\s+.*{term}.*",
            rf"^\s*from\s+.*{term}.*\s+import\s+.*",
        ]
    elif language in ("JavaScript", "TypeScript"):
        patterns = [
            rf"^\s*import\s+.*from\s+['\"].*{term}.*['\"]",
            rf".*require\s*\(\s*['\"].*{term}.*['\"]\s*\)",
        ]
    elif language == "Go":
        patterns = [
            rf'import\s+["\'].*{term}.*["\']',
            rf'["\'].*{term}.*["\']',
        ]
    elif language == "Java":
        patterns = [rf"^\s*import\s+.*{term}.*\s*;"]
    elif language == "Rust":
        patterns = [rf"^\s*use\s+.*{term}.*\s*;", rf"^\s*extern\s+crate\s+.*{term}.*\s*;"]
    elif language == "Ruby":
        patterns = [rf"^\s*require\s+['\"].*{term}.*['\"]"]
    elif language == "PHP":
        patterns = [rf"^\s*use\s+.*{term}.*\s*;", rf"^\s*require.*{term}.*"]
    elif language == "C#":
        patterns = [rf"^\s*using\s+.*{term}.*\s*;"]
    else:
        patterns = [rf".*import.*{term}.*", rf".*include.*{term}.*", rf".*require.*{term}.*"]

    seen: set[str] = set()
    for line in lines:
        stripped = line.strip()
        for pat in patterns:
            if re.search(pat, stripped, re.IGNORECASE):
                if stripped not in seen:
                    seen.add(stripped)
                    found.append(stripped)
                break
    return found


def _extract_snippets(lines: list[str], query_term: str, max_lines: int) -> list[str]:
    term_lower = query_term.lower()
    match_indices: list[int] = [
        i for i, line in enumerate(lines) if term_lower in line.lower()
    ]

    context = 3
    windows: list[tuple[int, int]] = []
    for idx in match_indices:
        start = max(0, idx - context)
        end = min(len(lines) - 1, idx + context)
        if windows and start <= windows[-1][1] + 1:
            windows[-1] = (windows[-1][0], end)
        else:
            windows.append((start, end))

    collected: list[str] = []
    total = 0
    for start, end in windows:
        chunk = lines[start : end + 1]
        if total + len(chunk) > max_lines:
            remaining = max_lines - total
            if remaining > 0:
                collected.append("\n".join(chunk[:remaining]))
            break
        collected.append("\n".join(chunk))
        total += len(chunk)

    return collected


def extract_usage(file_info: dict[str, Any], query: str) -> FileExtract:
    raw: str = file_info.get("raw_content") or ""
    file_path: str = file_info.get("file_path") or ""
    repo_name: str = file_info.get("repo_full_name") or ""
    repo_url: str = file_info.get("repo_url") or ""

    language = _detect_language(file_path)
    loc_score = _location_score(file_path)

    lines = raw.splitlines()
    term = query.strip()

    frequency = sum(1 for line in lines if term.lower() in line.lower())
    imports = _extract_imports(lines, term, language)
    snippets = _extract_snippets(lines, term, config.SEARCH_MAX_LINES_PER_FILE)

    return FileExtract(
        repo_name=repo_name,
        repo_url=repo_url,
        file_path=file_path,
        language=language,
        imports=imports,
        usage_snippets=snippets,
        frequency=frequency,
        location_score=loc_score,
        total_score=0.0,
    )