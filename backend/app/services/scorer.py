from __future__ import annotations

from app.models.schemas import FileExtract


def _compute_score(extract: FileExtract) -> float:
    frequency_score = min(extract.frequency, 20) / 20
    has_imports = 1.0 if extract.imports else 0.0
    snippet_richness = min(len(extract.usage_snippets), 10) / 10

    return (
        frequency_score * 0.4
        + extract.location_score * 0.3
        + has_imports * 0.2
        + snippet_richness * 0.1
    )


def score_and_filter(extracts: list[FileExtract], top_n: int = 30) -> list[FileExtract]:
    for extract in extracts:
        extract.total_score = _compute_score(extract)

    sorted_extracts = sorted(extracts, key=lambda e: e.total_score, reverse=True)
    return sorted_extracts[:top_n]