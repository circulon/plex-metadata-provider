"""
Dataclasses for the Plex-facing *output* schema - the JSON object Plex
expects back from a match/metadata request, per
https://developer.plex.tv/pms/#section/API-Info/Metadata-Providers.

Field names match Plex's own JSON keys exactly (``ratingKey``,
``originallyAvailableAt``, ``Genre``, ...); app/helper/mapper.py maps a
source's ``SourceMetadata`` (app/client/base.py) into this shape.

Class naming: every class here is ``Plex``-prefixed (``PlexMetadata``,
``PlexPerson``, ``PlexImage``, ...) to distinguish it from
app/client/base.py's differently-shaped, source-facing equivalents
(``PersonEntry``, ``ImageEntry``, ``RatingEntry``, ``SimilarEntry``). This
only affects Python identifiers - the dataclass *field* names inside
PlexMetadata (``Image``, ``Rating``, ``Guid``, ``Genre``, ...) are Plex's
own required JSON keys and are left exactly as Plex expects them.

``to_dict()`` (via the module-level ``serialize()``) drops any field left
at its default (None / empty list), so an unpopulated field is simply
absent from the response.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

# --- Plex's `type` field values (Metadata response, not the match-request
# integer - see app/helper/constants.MATCH_REQUEST_TYPE_* for that). ---
METADATA_TYPE_MOVIE = "movie"
METADATA_TYPE_SHOW = "show"
METADATA_TYPE_SEASON = "season"
METADATA_TYPE_EPISODE = "episode"
# Not part of Plex's documented custom-provider type set today - see
# app/client/source/music/example_music.py.
METADATA_TYPE_ARTIST = "artist"
METADATA_TYPE_ALBUM = "album"
METADATA_TYPE_TRACK = "track"

# Types which "contain child items" per
# https://developer.plex.tv/pms/#section/API-Info/Metadata-Providers - these
# respond to /children (and /grandchildren) and, per the general API docs'
# "one exception" note, use a /children-suffixed ``key`` in Metadata
# responses rather than the plain metadata path (see Mapper._base_metadata).
TYPES_WITH_CHILDREN: frozenset[str] = frozenset({METADATA_TYPE_SHOW, METADATA_TYPE_SEASON})

# Static parent/grandparent type inference for the movie/show/season/episode
# hierarchy - used to populate the required parentType/grandparentType (and,
# combined with a GUID, parentGuid/grandparentGuid) fields on season/episode
# Metadata objects. See app/helper/mapper.py._apply_hierarchy.
PARENT_TYPE_OF: dict[str, str] = {
    METADATA_TYPE_SEASON: METADATA_TYPE_SHOW,
    METADATA_TYPE_EPISODE: METADATA_TYPE_SEASON,
}
GRANDPARENT_TYPE_OF: dict[str, str] = {
    METADATA_TYPE_EPISODE: METADATA_TYPE_SHOW,
}


# ----------------------------------------------------------------------
# Array-item objects - one entry each in PlexMetadata's various array fields.
# ----------------------------------------------------------------------
@dataclass
class PlexTag:
    """The generic ``{"tag": "..."}`` shape shared by Genre/Country/Studio/
    Network array entries."""

    tag: str


@dataclass
class PlexGuid:
    id: str  # e.g. "imdb://tt0088763"


@dataclass
class PlexSimilar:
    guid: str
    tag: str | None = None


@dataclass
class PlexPerson:
    """One entry in Role/Director/Producer/Writer."""

    tag: str
    thumb: str | None = None
    role: str | None = None
    order: int | None = None


@dataclass
class PlexRating:
    value: float
    type: str = "audience"  # "audience" | "critic"
    image: str | None = None


@dataclass
class PlexImage:
    type: str  # "coverPoster" | "background" | "backgroundSquare" | "clearLogo" | "snapshot"
    url: str
    alt: str | None = None


@dataclass
class PlexChildren:
    """The ``Children`` object embedded in a parent Metadata object when
    ``includeChildren=1`` is requested (Metadata and Match features
    alike) - a simplified MediaContainer of the parent's direct children
    (Seasons for a Show, Episodes for a Season)."""

    size: int
    Metadata: list[dict] = field(default_factory=list)


# ----------------------------------------------------------------------
# The Metadata object itself.
# ----------------------------------------------------------------------
@dataclass
class PlexMetadata:
    """A single Plex ``Metadata`` object. Only ``ratingKey``/``key``/
    ``guid``/``type``/``title`` are required; everything else is included
    in the output only when set - see ``to_dict()``."""

    ratingKey: str
    key: str
    guid: str
    title: str
    type: str = METADATA_TYPE_MOVIE

    score: int | None = None
    originallyAvailableAt: str | None = None
    year: int | None = None
    summary: str | None = None
    originalTitle: str | None = None
    titleSort: str | None = None
    contentRating: str | None = None
    tagline: str | None = None
    studio: str | None = None
    isAdult: bool | None = None
    duration: int | None = None
    thumb: str | None = None
    art: str | None = None
    theme: str | None = None

    Image: list[PlexImage] = field(default_factory=list)
    OriginalImage: list[PlexImage] = field(default_factory=list)
    Genre: list[PlexTag] = field(default_factory=list)
    Guid: list[PlexGuid] = field(default_factory=list)
    Country: list[PlexTag] = field(default_factory=list)
    Role: list[PlexPerson] = field(default_factory=list)
    Director: list[PlexPerson] = field(default_factory=list)
    Producer: list[PlexPerson] = field(default_factory=list)
    Writer: list[PlexPerson] = field(default_factory=list)
    Similar: list[PlexSimilar] = field(default_factory=list)
    Studio: list[PlexTag] = field(default_factory=list)
    Rating: list[PlexRating] = field(default_factory=list)

    # --- Show only: networks the show aired on --------------------------
    Network: list[PlexTag] = field(default_factory=list)

    # --- Hierarchy fields (seasons/episodes, albums/tracks) -----------------
    parentRatingKey: str | None = None
    parentKey: str | None = None
    parentGuid: str | None = None
    parentType: str | None = None
    parentTitle: str | None = None
    parentThumb: str | None = None
    grandparentRatingKey: str | None = None
    grandparentKey: str | None = None
    grandparentGuid: str | None = None
    grandparentType: str | None = None
    grandparentTitle: str | None = None
    grandparentThumb: str | None = None
    # Season number (season type) / episode number (episode type) / track
    # number (track type).
    index: int | None = None
    # Season number, for an episode. Disc number, for a track.
    parentIndex: int | None = None

    # --- Children (TV Shows/Seasons only) -----------------------------------
    # Populated only when the caller requested includeChildren=1 - see
    # app/service/metadata.py and app/service/match.py.
    Children: PlexChildren | None = None

    # If set on a Show, indicates it has no Seasons and a client should use
    # /grandchildren instead of /children. If set on an Episode, indicates
    # its Season is itself skipped (e.g. podcasts). See
    # https://developer.plex.tv/pms/#section/API-Info/Metadata-Providers.
    skipChildren: bool | None = None
    skipParent: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return serialize(self)


# ----------------------------------------------------------------------
# Generic dataclass -> plain-dict serialization, dropping unset fields.
# ----------------------------------------------------------------------
def serialize(obj: Any) -> Any:
    """Turns a dataclass into a plain dict via ``dataclasses.asdict()``,
    then strips any ``None`` or empty-list value."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return _drop_empty(asdict(obj))
    return obj


def _drop_empty(value: Any) -> Any:
    """Recursively drops any dict entry whose value is ``None`` or an
    empty list."""
    if isinstance(value, dict):
        cleaned = {k: _drop_empty(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v is not None and v != []}
    if isinstance(value, list):
        return [_drop_empty(v) for v in value]
    return value
