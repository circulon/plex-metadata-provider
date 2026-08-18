"""
Environment-driven configuration.

Metadata sources are enabled per category (movie/show/season/episode/music
- see app/helper/constants.SOURCE_TYPES), via two env vars each:

  ENABLE_<CATEGORY>_SOURCES=true|false   # category on/off
  <CATEGORY>_SOURCES=first,second,...    # which sources, in priority order

See app/client/registry.py for how these are resolved to source classes.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _list_env(name: str, default: list[str]) -> list[str]:
    """Parses a comma-separated env var into an ordered list. Blank entries
    and whitespace are dropped; an unset/empty var falls back to
    ``default``."""
    val = os.environ.get(name)
    if val is None:
        return list(default)
    items = [item.strip() for item in val.split(",")]
    items = [item for item in items if item]
    return items or list(default)


class Config:
    # --- Provider identity -------------------------------------------------
    # Must be prefixed with "tv.plex.agents.custom.", globally unique, and
    # should not end with a type suffix like ".movie" (construct_guid()
    # already appends the type after "://"). See
    # docs/MediaProvider.md#defining-an-identifier in
    # https://github.com/plexinc/tmdb-example-provider.
    PROVIDER_IDENTIFIER: str = os.environ.get("PROVIDER_IDENTIFIER", "tv.plex.agents.custom.yourname.template")
    PROVIDER_TITLE: str = os.environ.get("PROVIDER_TITLE", "Metadata Provider Template")
    PROVIDER_VERSION: str = os.environ.get("PROVIDER_VERSION", "1.0.0")

    PROVIDER_USER_AGENT = os.environ.get("PROVIDER_USER_AGENT", "MetadataProviderTemplate/1.0")

    # Whether to append a source's optional `summary_extra` text to the
    # `summary` field - see app/client/base.SourceMetadata.summary_extra.
    INCLUDE_EXTRA_IN_SUMMARY: bool = _bool_env("INCLUDE_EXTRA_IN_SUMMARY", True)

    # --- Matching/scoring thresholds (0-100 rapidfuzz composite score) -----
    # EXACT_IGNORE_SCORE: bar for automatic (non-manual) matching.
    # MANUAL_IGNORE_SCORE: lower bar for manual/"fix match" requests, which
    # return a ranked list for a person to choose from.
    EXACT_IGNORE_SCORE: int = int(os.environ.get("EXACT_IGNORE_SCORE", "85"))
    MANUAL_IGNORE_SCORE: int = int(os.environ.get("MANUAL_IGNORE_SCORE", "65"))

    # --- Response paging (manual match requests) ----------------------------
    DEFAULT_PAGE_SIZE: int = int(os.environ.get("DEFAULT_PAGE_SIZE", "20"))

    # --- Flask / server ------------------------------------------------------
    PORT: int = int(os.environ.get("PORT", "32900"))
    DEBUG: bool = _bool_env("DEBUG", False)
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()

    # --- Source client caches (shared across all enabled sources) ----------
    ENTRY_CACHE_TTL_SECONDS: int = int(os.environ.get("ENTRY_CACHE_TTL_SECONDS", "60"))
    ENTRY_CACHE_MAX_SIZE: int = int(os.environ.get("ENTRY_CACHE_MAX_SIZE", "2000"))
    SEARCH_CACHE_TTL_SECONDS: int = int(os.environ.get("SEARCH_CACHE_TTL_SECONDS", "60"))
    SEARCH_CACHE_MAX_SIZE: int = int(os.environ.get("SEARCH_CACHE_MAX_SIZE", "500"))

    # --- Metadata sources: enable/disable + search order, per category -----
    ENABLE_MOVIE_SOURCES: bool = _bool_env("ENABLE_MOVIE_SOURCES", True)
    ENABLE_SHOW_SOURCES: bool = _bool_env("ENABLE_SHOW_SOURCES", True)
    # season/episode are enabled by default but ship no default source - see
    # app/client/source/season/__init__.py and .../episode/__init__.py.
    ENABLE_SEASON_SOURCES: bool = _bool_env("ENABLE_SEASON_SOURCES", True)
    ENABLE_EPISODE_SOURCES: bool = _bool_env("ENABLE_EPISODE_SOURCES", True)
    # Off by default - see app/helper/constants.py.
    ENABLE_MUSIC_SOURCES: bool = _bool_env("ENABLE_MUSIC_SOURCES", False)

    MOVIE_SOURCES: list[str] = _list_env("MOVIE_SOURCES", ["example_movie"])
    SHOW_SOURCES: list[str] = _list_env("SHOW_SOURCES", ["example_show"])
    SEASON_SOURCES: list[str] = _list_env("SEASON_SOURCES", [])
    EPISODE_SOURCES: list[str] = _list_env("EPISODE_SOURCES", [])
    MUSIC_SOURCES: list[str] = _list_env("MUSIC_SOURCES", ["example_music"])


class TestConfig(Config):
    """Every field pinned to its documented default rather than inherited
    from Config's `os.environ` reads, so a local .env can't affect test
    results."""

    DEBUG = True
    TESTING = True

    PROVIDER_IDENTIFIER: str = "tv.plex.agents.custom.yourname.template"
    PROVIDER_TITLE: str = "Media Provider Template"
    PROVIDER_VERSION: str = "1.0.0"
    PROVIDER_USER_AGENT: str = "MediaProviderTemplate/1.0"

    INCLUDE_EXTRA_IN_SUMMARY: bool = True

    EXACT_IGNORE_SCORE: int = 85
    MANUAL_IGNORE_SCORE: int = 65

    DEFAULT_PAGE_SIZE: int = 20

    ENTRY_CACHE_TTL_SECONDS: int = 60
    ENTRY_CACHE_MAX_SIZE: int = 2000
    SEARCH_CACHE_TTL_SECONDS: int = 60
    SEARCH_CACHE_MAX_SIZE: int = 500

    ENABLE_MOVIE_SOURCES: bool = True
    ENABLE_SHOW_SOURCES: bool = True
    ENABLE_SEASON_SOURCES: bool = True
    ENABLE_EPISODE_SOURCES: bool = True
    ENABLE_MUSIC_SOURCES: bool = False
    MOVIE_SOURCES: list[str] = ["example_movie"]
    SHOW_SOURCES: list[str] = ["example_show"]
    SEASON_SOURCES: list[str] = []
    EPISODE_SOURCES: list[str] = []
    MUSIC_SOURCES: list[str] = ["example_music"]
