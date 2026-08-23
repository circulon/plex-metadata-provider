"""
Environment-driven configuration.

Metadata sources are enabled per category (movie/show/season/episode/artist
- see app/helper/constants.SOURCE_TYPES), via two env vars each:

  ENABLE_<CATEGORY>_SOURCES=true|false   # category on/off
  <CATEGORY>_SOURCES=first,second,...    # which sources, in priority order

Each pair also gets a ``SourceCategorySettings`` entry in
``Config.SOURCE_CATEGORIES``, keyed by category and built from direct
attribute references (dot notation) rather than string-built dict keys.
``validate_source_categories()`` (called from ``create_app()``) checks that
every category in app/helper/constants.SOURCE_TYPES has an entry.

See app/client/registry.py for how these are resolved to source classes.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
import tomllib

from dotenv import load_dotenv

from app.helper.constants import SOURCE_TYPES, SourceType

load_dotenv()


@dataclass(frozen=True)
class SourceCategorySettings:
    """One category's on/off switch bundled with its ordered source list,
    looked up together via a single attribute
    (``cfg.SOURCE_CATEGORIES[category]``)."""

    enabled: bool
    sources: list[str]


@lru_cache
def _get_version() -> str:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        with open(pyproject_path, "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except Exception:
        return "0.0.0-dev"


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
    # should not end with a generic type suffix like ".movie".
    # See docs/MediaProvider.md#defining-an-identifier in
    # https://github.com/plexinc/tmdb-example-provider.
    PROVIDER_IDENTIFIER: str = "tv.plex.agents.custom.yourname.template"
    PROVIDER_TITLE: str = "Metadata Provider Template"
    PROVIDER_VERSION: str = _get_version()
    PROVIDER_USER_AGENT = f"MetadataProviderTemplate/{PROVIDER_VERSION:.1}"

    # --- Metadata sources: enable/disable + search order, per category -----
    # Movies
    ENABLE_MOVIE_SOURCES: bool = True
    MOVIE_SOURCES: list[str] = ["example_movie"]

    # TV Shows
    ENABLE_SHOW_SOURCES: bool = False
    SHOW_SOURCES: list[str] = ["example_show"]
    ENABLE_SEASON_SOURCES: bool = False
    SEASON_SOURCES: list[str] = []
    ENABLE_EPISODE_SOURCES: bool = False
    EPISODE_SOURCES: list[str] = []

    # Music
    # Currently unused but implemented for future availability
    # see PLEX_SUPPORTED_MATCH_TYPES in app/helper/constants.py
    # when usage becomes available
    ENABLE_ARTIST_SOURCES: bool = False
    ARTIST_SOURCES: list[str] = ["example_artist"]
    ENABLE_ALBUM_SOURCES: bool = False
    ALBUM_SOURCES: list[str] = []
    ENABLE_TRACK_SOURCES: bool = False
    TRACK_SOURCES: list[str] = []

    # Whether to append a source's optional `summary_extra` text to the
    # `summary` field - see app/client/base.SourceMetadata.summary_extra.
    INCLUDE_EXTRA_IN_SUMMARY: bool = _bool_env("INCLUDE_EXTRA_IN_SUMMARY", True)

    # --- Matching/scoring thresholds (0-100) -----
    # MINIMUM_EXACT_SCORE: Minimum for automatic (non-manual) matching consideration.
    # MINIMUM_MANUAL_SCORE: minimum for "match"/"fix match" requests, which
    # return a ranked list consideration.
    MINIMUM_EXACT_SCORE: int = int(os.environ.get("MINIMUM_EXACT_SCORE", "85"))
    MINIMUM_MANUAL_SCORE: int = int(os.environ.get("MINIMUM_MANUAL_SCORE", "65"))

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

    # --- Grouped, per-category view of the above (see module docstring) ----
    SOURCE_CATEGORIES: dict[SourceType, SourceCategorySettings] = {
        SourceType.MOVIE: SourceCategorySettings(ENABLE_MOVIE_SOURCES, MOVIE_SOURCES),
        SourceType.SHOW: SourceCategorySettings(ENABLE_SHOW_SOURCES, SHOW_SOURCES),
        SourceType.SEASON: SourceCategorySettings(ENABLE_SEASON_SOURCES, SEASON_SOURCES),
        SourceType.EPISODE: SourceCategorySettings(ENABLE_EPISODE_SOURCES, EPISODE_SOURCES),
        SourceType.ARTIST: SourceCategorySettings(ENABLE_ARTIST_SOURCES, ARTIST_SOURCES),
        SourceType.ALBUM: SourceCategorySettings(ENABLE_ALBUM_SOURCES, ALBUM_SOURCES),
        SourceType.TRACK: SourceCategorySettings(ENABLE_TRACK_SOURCES, TRACK_SOURCES),
    }


class TestConfig(Config):
    """Every field pinned to its documented default rather than inherited
    from Config's `os.environ` reads, so a local .env can't affect test
    results."""

    DEBUG = True
    TESTING = True

    PROVIDER_IDENTIFIER: str = "tv.plex.agents.custom.yourname.template"
    PROVIDER_TITLE: str = "Metadata Provider Template"
    PROVIDER_VERSION: str = "1.0.0"
    PROVIDER_USER_AGENT: str = "MetadataProviderTemplate/1.0"

    # Movies
    ENABLE_MOVIE_SOURCES: bool = True
    MOVIE_SOURCES: list[str] = ["example_movie"]

    # TV Shows
    ENABLE_SHOW_SOURCES: bool = True
    SHOW_SOURCES: list[str] = ["example_show"]
    ENABLE_SEASON_SOURCES: bool = True
    SEASON_SOURCES: list[str] = []
    ENABLE_EPISODE_SOURCES: bool = True
    EPISODE_SOURCES: list[str] = []



    INCLUDE_EXTRA_IN_SUMMARY: bool = True

    # --- Matching/scoring thresholds (0-100) -----
    # MINIMUM_EXACT_SCORE: threshold for automatic (non-manual) matching.
    # MINIMUM_MANUAL_SCORE: lower threshold for manual "fix match" requests
    MINIMUM_EXACT_SCORE: int = int(os.environ.get("MINIMUM_EXACT_SCORE", "85"))
    MINIMUM_MANUAL_SCORE: int = int(os.environ.get("MINIMUM_MANUAL_SCORE", "65"))

    DEFAULT_PAGE_SIZE: int = 20

    ENTRY_CACHE_TTL_SECONDS: int = 60
    ENTRY_CACHE_MAX_SIZE: int = 2000
    SEARCH_CACHE_TTL_SECONDS: int = 60
    SEARCH_CACHE_MAX_SIZE: int = 500

    # Artist/album/track aren't overridden above, so they're pulled from
    # Config explicitly - bare names in this class body only resolve to
    # names assigned in *this* body, not inherited ones.
    SOURCE_CATEGORIES: dict[SourceType, SourceCategorySettings] = {
        SourceType.MOVIE: SourceCategorySettings(ENABLE_MOVIE_SOURCES, MOVIE_SOURCES),
        SourceType.SHOW: SourceCategorySettings(ENABLE_SHOW_SOURCES, SHOW_SOURCES),
        SourceType.SEASON: SourceCategorySettings(ENABLE_SEASON_SOURCES, SEASON_SOURCES),
        SourceType.EPISODE: SourceCategorySettings(ENABLE_EPISODE_SOURCES, EPISODE_SOURCES),
        SourceType.ARTIST: SourceCategorySettings(Config.ENABLE_ARTIST_SOURCES, Config.ARTIST_SOURCES),
        SourceType.ALBUM: SourceCategorySettings(Config.ENABLE_ALBUM_SOURCES, Config.ALBUM_SOURCES),
        SourceType.TRACK: SourceCategorySettings(Config.ENABLE_TRACK_SOURCES, Config.TRACK_SOURCES),
    }


def validate_source_categories(config_object: type[Config]) -> None:
    """Checks that ``config_object.SOURCE_CATEGORIES`` has exactly one
    ``SourceCategorySettings`` entry per category in
    ``app.helper.constants.SOURCE_TYPES`` - no missing or stray categories.
    Called from ``create_app()`` so a misconfiguration surfaces at startup
    rather than on the first request that touches the affected category."""
    categories = getattr(config_object, "SOURCE_CATEGORIES", None)
    if not isinstance(categories, dict):
        raise RuntimeError(
            f"{config_object.__name__}.SOURCE_CATEGORIES is missing or not a dict - "
            "see app/helper/config.py."
        )

    missing = [c for c in SOURCE_TYPES if c not in categories]
    if missing:
        raise RuntimeError(
            f"{config_object.__name__}.SOURCE_CATEGORIES is missing entries for: "
            f"{', '.join(missing)}. Every category in app.helper.constants.SOURCE_TYPES "
            "needs a SourceCategorySettings entry."
        )

    extra = [c for c in categories if c not in SOURCE_TYPES]
    if extra:
        raise RuntimeError(
            f"{config_object.__name__}.SOURCE_CATEGORIES has entries not in "
            f"app.helper.constants.SOURCE_TYPES: {', '.join(extra)}."
        )

    not_settings = [c for c, v in categories.items() if not isinstance(v, SourceCategorySettings)]
    if not_settings:
        raise RuntimeError(
            f"{config_object.__name__}.SOURCE_CATEGORIES entries for {', '.join(not_settings)} "
            "aren't SourceCategorySettings instances."
        )
