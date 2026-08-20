"""
Shared constants: Plex's metadata type numbers, and the source-category
routing table built on top of them.
"""
from __future__ import annotations

from enum import IntEnum, StrEnum

# API path constants
URL_PREFIX_METADATA = "/metadata"
URL_PREFIX_MATCHES = "/matches"


class MatchRequestType(IntEnum):
    """Plex's metadata type numbers, as used in the match-request ``type``
    field and the MediaProvider ``Types`` array."""

    MOVIE = 1
    SHOW = 2
    SEASON = 3
    EPISODE = 4
    # Currently not accepted by Plex's custom-provider API - see
    # app/client/source/artist/example_artist.py. Kept for forward-looking
    # scaffolding.
    ARTIST = 8
    ALBUM = 9
    TRACK = 10


class SourceType(StrEnum):
    """One member per app/client/source/<category>/ package (see
    app/client/registry.py), and per ENABLE_<CATEGORY>_SOURCES /
    <CATEGORY>_SOURCES env-var pair (app/helper/config.py). Each member's
    value is also its package directory name. Each category maps to
    exactly one MatchRequestType."""

    MOVIE = "movie"
    SHOW = "show"
    SEASON = "season"
    EPISODE = "episode"
    ARTIST = "artist"
    ALBUM = "album"
    TRACK = "track"


SOURCE_TYPES: tuple[SourceType, ...] = tuple(SourceType)

# Which match-request type each source category serves.
SOURCE_CATEGORY_MATCH_TYPES: dict[SourceType, MatchRequestType] = {
    SourceType.MOVIE: MatchRequestType.MOVIE,
    SourceType.SHOW: MatchRequestType.SHOW,
    SourceType.SEASON: MatchRequestType.SEASON,
    SourceType.EPISODE: MatchRequestType.EPISODE,
    SourceType.ARTIST: MatchRequestType.ARTIST,
    SourceType.ALBUM: MatchRequestType.ALBUM,
    SourceType.TRACK: MatchRequestType.TRACK,
}

# The subset of match types Plex's custom-provider API currently accepts -
# used to build the MediaProvider "Types" array (see app/routes.py).
PLEX_SUPPORTED_MATCH_TYPES: set[MatchRequestType] = {
    MatchRequestType.MOVIE,
    MatchRequestType.SHOW,
    MatchRequestType.SEASON,
    MatchRequestType.EPISODE,
}


def match_type_to_source_category(match_type: int | None) -> SourceType | None:
    """e.g. ``MatchRequestType.SHOW -> SourceType.SHOW``. Returns None for
    an unrecognized type - callers treat that as a 400."""
    for category, type_ in SOURCE_CATEGORY_MATCH_TYPES.items():
        if match_type == type_:
            return category
    return None
