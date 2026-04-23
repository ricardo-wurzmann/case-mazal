from __future__ import annotations

import math
from datetime import datetime, timezone

from app.models.schemas import FileExtract


def _repo_health_score(extract: FileExtract) -> float:
    """
    Score 0-1 baseado em atividade e saúde do repositório.
    Penaliza repos arquivados ou abandonados há mais de 2 anos.
    """
    # Recência: decai linearmente até 0 aos 730 dias de inatividade
    pushed_at = extract.repo_pushed_at or ""
    if pushed_at:
        try:
            dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
            days_inactive = (datetime.now(timezone.utc) - dt).days
            recency = max(0.0, 1.0 - days_inactive / 730)
        except ValueError:
            recency = 0.5
    else:
        recency = 0.5  # neutro se dado ausente

    # Popularidade em log scale: 0 stars→0.0, ~100 stars→0.67, ~1000 stars→1.0
    popularity = min(1.0, math.log1p(extract.repo_stars) / math.log1p(1000))

    # Repos arquivados recebem penalidade total no componente
    archive_factor = 0.0 if extract.repo_archived else 1.0

    # Recência pesa mais: repo ativo com poucos stars > repo famoso abandonado
    return round(recency * 0.55 + popularity * 0.25 + archive_factor * 0.20, 3)


def _compute_score(extract: FileExtract) -> float:
    frequency_score = min(extract.frequency, 20) / 20
    has_imports = 1.0 if extract.imports else 0.0
    snippet_richness = min(len(extract.usage_snippets), 10) / 10

    heuristic = (
        frequency_score * 0.4
        + extract.location_score * 0.3
        + has_imports * 0.2
        + snippet_richness * 0.1
    )

    health = _repo_health_score(extract)

    # Heurístico continua dominante; saúde do repo entra como fator de confiança
    return round(heuristic * 0.75 + health * 0.25, 4)


def score_and_filter(extracts: list[FileExtract], top_n: int = 30) -> list[FileExtract]:
    for extract in extracts:
        extract.total_score = _compute_score(extract)

    sorted_extracts = sorted(extracts, key=lambda e: e.total_score, reverse=True)
    return sorted_extracts[:top_n]