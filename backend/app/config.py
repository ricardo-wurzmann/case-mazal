import os

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    return int(v)


GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
SEARCH_MAX_REPOS: int = _int("SEARCH_MAX_REPOS", 30)
SEARCH_MAX_FILES_PER_REPO: int = _int("SEARCH_MAX_FILES_PER_REPO", 5)
SEARCH_MAX_LINES_PER_FILE: int = _int("SEARCH_MAX_LINES_PER_FILE", 50)
GITHUB_API_VERSION: str = "2022-11-28"
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "minimax/minimax-m2.5:free")