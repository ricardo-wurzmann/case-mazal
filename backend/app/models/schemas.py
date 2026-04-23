from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)


# --- Project mode ---

class ProjectRequest(BaseModel):
    idea: str = Field(..., min_length=10, max_length=1000)


class SubproblemInfo(BaseModel):
    name: str
    description: str
    query: str
    repos_found: int = 0
    files_found: int = 0


class FileExtract(BaseModel):
    repo_name: str
    repo_url: str
    file_path: str
    language: str
    imports: list[str]
    usage_snippets: list[str]
    frequency: int
    location_score: float
    total_score: float = 0.0
    subproblem: str = ""


class SearchStats(BaseModel):
    total_repos: int
    total_files: int
    languages: dict[str, int] = Field(default_factory=dict)
    top_repos: list[str] = Field(default_factory=list)
    min_top_score: float = 0.0
    subproblems: list[SubproblemInfo] = Field(default_factory=list)
    detected_language: str = "python"


class SearchResponse(BaseModel):
    query: str
    stats: SearchStats
    analysis: str
    extracts: list[FileExtract]