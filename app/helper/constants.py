"""
Shared constants: Plex's metadata type numbers, and the source-category
routing table built on top of them.
"""
from __future__ import annotations

# API path constants
LIBRARY_METADATA = "/metadata"
LIBRARY_MATCHES = "/matches"

# --- Plex metadata type numbers (match-request "type" field) --------------
MATCH_REQUEST_TYPE_MOVIE = 1
MATCH_REQUEST_TYPE_SHOW = 2
MATCH_REQUEST_TYPE_SEASON = 3
MATCH_REQUEST_TYPE_EPISODE = 4
# Not accepted by Plex's custom-provider API today - see
# app/client/source/music/example_music.py. Kept for forward-looking
# scaffolding; ENABLE_MUSIC_SOURCES defaults to False.
MATCH_REQUEST_TYPE_ARTIST = 8
MATCH_REQUEST_TYPE_ALBUM = 9
MATCH_REQUEST_TYPE_TRACK = 10

# --- Source categories -------------------------------------------------
# One category per app/client/source/<category>/ package (see
# app/client/registry.py), and one ENABLE_<CATEGORY>_SOURCES /
# <CATEGORY>_SOURCES env-var pair per category (app/helper/config.py).
# Each category maps to exactly one Plex metadata type, except MUSIC
# (artist/album/track), which stays grouped since none of it is
# Plex-supported yet.
SOURCE_TYPE_MOVIE = "movie"
SOURCE_TYPE_SHOW = "show"
SOURCE_TYPE_SEASON = "season"
SOURCE_TYPE_EPISODE = "episode"
SOURCE_TYPE_MUSIC = "music"

SOURCE_TYPES: tuple[str, ...] = (
    SOURCE_TYPE_MOVIE, SOURCE_TYPE_SHOW, SOURCE_TYPE_SEASON, SOURCE_TYPE_EPISODE, SOURCE_TYPE_MUSIC,
)

# Which match-request type(s) each source category serves.
SOURCE_CATEGORY_MATCH_TYPES: dict[str, set[int]] = {
    SOURCE_TYPE_MOVIE: {MATCH_REQUEST_TYPE_MOVIE},
    SOURCE_TYPE_SHOW: {MATCH_REQUEST_TYPE_SHOW},
    SOURCE_TYPE_SEASON: {MATCH_REQUEST_TYPE_SEASON},
    SOURCE_TYPE_EPISODE: {MATCH_REQUEST_TYPE_EPISODE},
    SOURCE_TYPE_MUSIC: {MATCH_REQUEST_TYPE_ARTIST, MATCH_REQUEST_TYPE_ALBUM, MATCH_REQUEST_TYPE_TRACK},
}

# The subset of match types Plex's custom-provider API currently accepts -
# used to build the MediaProvider "Types" array (see app/routes.py).
PLEX_SUPPORTED_MATCH_TYPES: set[int] = {
    MATCH_REQUEST_TYPE_MOVIE, MATCH_REQUEST_TYPE_SHOW, MATCH_REQUEST_TYPE_SEASON, MATCH_REQUEST_TYPE_EPISODE,
}


def match_type_to_source_category(match_type: int | None) -> str | None:
    """e.g. ``MATCH_REQUEST_TYPE_SHOW -> "show"``. Returns None for an
    unrecognized type - callers treat that as a 400."""
    for category, types in SOURCE_CATEGORY_MATCH_TYPES.items():
        if match_type in types:
            return category
    return None
