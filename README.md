# Plex Metadata Provider Template

A baseline template for building Plex ["Custom Metadata
Providers"](https://developer.plex.tv/pms/#section/API-Info/Metadata-Providers)
— movies, TV shows, and (as forward-looking scaffolding) music. Adding a
new metadata source is a matter of dropping in one file and flipping an
env var.

Implements the HTTP contract documented by Plex's own example provider
(https://github.com/plexinc/tmdb-example-provider) and
https://developer.plex.tv/pms/#section/API-Info/Metadata-Providers:

```
GET  /                                            -> Provider definition
GET  /metadata/<ratingKey>                -> Metadata feature
                                                      (?includeChildren=1, ?episodeOrder=)
GET  /metadata/<ratingKey>/children        -> Direct children (Seasons of a Show,
                                                      Episodes of a Season). TV Shows/Seasons
                                                      only. Mandatory paging, defaults to 20.
GET  /metadata/<ratingKey>/grandchildren    -> Episodes of a Show, flattening past
                                                      Seasons. TV Shows only. Mandatory
                                                      paging, defaults to 20.
GET  /metadata/<ratingKey>/images          -> Image list for an item
GET  /metadata/<ratingKey>/extras          -> Extras list for an item
POST /matches                     -> Match feature
                                                      (includeChildren, episodeOrder)
GET  /health                                        -> Liveness check
```

## Quick start

```bash
cp .env.example .env
pip install -r requirements-dev.txt
python run.py
curl localhost:32900/
```

`ENABLE_MOVIE_SOURCES` is on by default with a
working, keyless example source. 

## Configure your provider

Update the configuration defaults below in `app/helper.config`and `.env.example`.

Then copy the `.env.example` to `.env` and restart the app.

### Provider identity

- `PROVIDER_IDENTIFIER`
  - this is the unique identifier Plex uses for your Provider. see [Defining an identifier section](https://developer.plex.tv/pms/#section/API-Info/Metadata-Providers)
- `PROVIDER_TITLE` 
  - This is the name of your provider shown in the Plex interface
- `PROVIDER_USER_AGENT` 
  - optionally used for calls to upstram API's and websites 

### Select source categories

Each source category maps 1:1 to a Plex metadata type — `movie`(1),
`show`(2), `season`(3), `episode`(4) — except `music`, which stays grouped
(artist/album/track) since none of it is Plex-supported yet (see "Music
support" below).

Plex recommends one metadata category per provider deployment. This template
doesn't enforce this, enable only the types that support the category you need.
eg for the TV Show category enable types 2,3,4 (show, season, episode) together in the app.

### Other default options

These are explained in `app/helper/config.py`

## App Architecture

```
app/
  client/
    base.py            # SourceClient protocol + SourceMetadata
    caching.py          # TTL-caching decorator around a SourceClient
    registry.py          # discovers + builds enabled sources, per category
    source/
      movie/example_movie.py    # Studio Ghibli API (free, no key)
      show/example_show.py       # TVMaze API (free, no key)
      season/                     # no example source - see __init__.py
      episode/                     # no example source - see __init__.py
      music/example_music.py       # MusicBrainz API (free, no key)
  schema/
    plex.py             # Plex-facing output schema (PlexMetadata)
    match_request.py     # incoming POST /matches body, typed
  helper/
    config.py             # env-driven Config
    constants.py            # Plex type numbers, source-category routing
    mapper.py                 # SourceMetadata -> PlexMetadata
  service/
    search.py             # holds an ordered client list, resolves ratingKeys
    match.py                # scoring, thresholds, category routing
    metadata.py               # GET /metadata/<ratingKey> (+images/extras)
  util/
    scoring.py    # rapidfuzz-based title relevance scoring
    text_utils.py  # normalization helpers
    ttl_cache.py    # thread-safe TTL cache
  routes.py    # Flask blueprint
  __init__.py   # application factory
```

A source translates its upstream shape into `SourceMetadata`
(`app/client/base.py`), field-aligned with Plex's own Metadata object.
Everything downstream only touches `SourceMetadata`, never a source's raw
shape.

Class naming: `app/client/base.py` (source-facing) uses `SourceMetadata`,
`PersonEntry`, `ImageEntry`, `RatingEntry`, `SimilarEntry`.
`app/schema/plex.py` (Plex-facing output) uses `PlexMetadata`,
`PlexPerson`, `PlexImage`, `PlexRating`, `PlexSimilar`, `PlexTag`,
`PlexGuid`. The dataclass *field* names inside `PlexMetadata` (`Image`,
`Rating`, `Guid`, `Genre`, ...) are Plex's own required JSON keys, left
as-is.

## Adding a source

1. Pick a category (`movie`, `show`, `season`, `episode`, `music`).
2. Add `app/client/source/<category>/your_source.py` with:
   - a class `YourSource` (snake_case filename → PascalCase), with a
     `name` attribute equal to its own module's filename, implementing
     `search()`/`get_entry()` per `SourceClient` (`app/client/base.py`).
     See the three example sources. A `show`/`season` source can also
     optionally implement `get_children()` to support `/children`,
     `/grandchildren`, and `includeChildren` - see "Children" below.
   - optionally, a fully-defaulted `YourSourceConfig` dataclass. A
     `user_agent` field is auto-filled from `Config.PROVIDER_USER_AGENT`.
3. Add `"your_source"` to that category's `<CATEGORY>_SOURCES` env var.

A module that doesn't follow the naming convention, or a name in
`<CATEGORY>_SOURCES` with no matching module, is logged and skipped rather
than crashing the app.

## Enabling sources

```env
ENABLE_MOVIE_SOURCES=true|false
MOVIE_SOURCES=first_source,second_source,...

ENABLE_SHOW_SOURCES=true|false
SHOW_SOURCES=example_show

ENABLE_SEASON_SOURCES=true|false
SEASON_SOURCES=

ENABLE_EPISODE_SOURCES=true|false
EPISODE_SOURCES=

ENABLE_MUSIC_SOURCES=true|false
MUSIC_SOURCES=example_music
```

`ENABLE_<CATEGORY>_SOURCES=false` disables the whole category regardless of
`<CATEGORY>_SOURCES`. Within an enabled category, `<CATEGORY>_SOURCES` is
both the allow-list and the priority order sources are tried in.

## Routing a match request

`POST /matches` receives Plex's numeric `type` field
(`app/helper/constants.MATCH_REQUEST_TYPE_*`). `MatchService` maps it to a
source category via `match_type_to_source_category()`. An unrecognized
type, or one mapping to a category with no enabled sources, is a `400`
(`UnsupportedMatchType`).

## Example sources

| Category | Source | Upstream | Notes |
|---|---|---|---|
| movie | `example_movie` | [Studio Ghibli API](https://ghibliapi.vercel.app) | No server-side search — fetches the catalog and filters locally. |
| show | `example_show` | [TVMaze API](https://www.tvmaze.com/api) | Server-side search; only produces `show` entries. |
| season | *(none)* | — | Enabled by default, no source — see `app/client/source/season/__init__.py`. |
| episode | *(none)* | — | Enabled by default, no source — see `app/client/source/episode/__init__.py`. |
| music | `example_music` | [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API) | See "Music support" below before enabling. |

## Music support

Plex's custom-provider API currently documents support for only
movie/show/season/episode; music libraries aren't supported yet.
`ENABLE_MUSIC_SOURCES` defaults to `false`, and `app/routes.py`'s
`MediaProvider` response never advertises artist/album/track types even if
music sources are enabled locally (`PLEX_SUPPORTED_MATCH_TYPES` in
`app/helper/constants.py`). Treat `music` as scaffolding for when/if Plex
adds support, or for a non-Plex internal use of the same contract.

## Adding season/episode/album/track support

`SourceMetadata` and `PlexMetadata` already carry the parent/grandparent
fields (`parent_title`, `grandparent_title`, `index`, `parent_index`, ...)
needed for hierarchical types. To add one:

1. Add a source module under `season`, `episode`, or a new album/track
   music source.
2. Fetch the child list from your chosen upstream.
3. Set `metadata_type=METADATA_TYPE_SEASON` / `EPISODE` / `ALBUM` / `TRACK`
   (`app.schema.plex`) on each entry.
4. Populate `parent_upstream_id`/`parent_title`/`grandparent_*`/`index`/
   `parent_index`, the same way `example_movie.py`/`example_show.py`
   populate their top-level fields.

No changes to `Mapper` or `MatchService` are needed.

`parentType`/`grandparentType`/`parentGuid`/`grandparentGuid` are inferred
automatically for the built-in movie/show/season/episode hierarchy
(`PARENT_TYPE_OF`/`GRANDPARENT_TYPE_OF` in `app/schema/plex.py`) - a
source only needs to set the `*_upstream_id`/`*_title` fields.

## Children (`/children`, `/grandchildren`, `includeChildren`)

For items which contain child items (TV Shows and Seasons), Plex expects
`/metadata/<ratingKey>/children` and `/grandchildren`, plus an
optional embedded `Children` object on the Metadata and Match features via
`includeChildren=1`. This template wires all three onto one optional
`SourceClient` method:

```python
def get_children(self, rating_key: str, episode_order: str | None = None) -> list[SourceMetadata] | None:
    ...
```

- A Show source implements this to return its Seasons; a Season source
  implements it to return its Episodes. See
  `app/client/base.SourceClient.get_children` for the full contract
  (return `[]` for "found, no children"; `None`/omit entirely for "this
  source doesn't do children").
- `GET .../children` calls it once; `GET .../grandchildren` calls it twice
  for a Show (Seasons, then each Season's Episodes) and flattens the
  result; both endpoints enforce Plex's mandatory paging (20 items by
  default - `X-Plex-Container-Size`/`-Start`).
- `?includeChildren=1` on the Metadata feature, and `includeChildren: 1` in
  a Match request body, embed the same direct-children list as a
  `Children` object on the returned Metadata object(s) - required support
  for TV Shows/Seasons, a no-op for other types.
- `episodeOrder` (Metadata query param, or a Match request field) is
  passed through to `get_children()` as-is; a source with only one episode
  ordering can safely ignore it. Full multi-ordering support (the
  `SeasonType` array) isn't implemented here - add it to your source and
  `Mapper`/`PlexMetadata` if you need it.
- No example source implements `get_children()` out of the box (TVMaze,
  the example show source, does expose a seasons/episodes API - wiring it
  up is a good first extension).

### A note on `key`

Per the general API docs: *"the type describes what will be returned when
fetching \[a\] key... One exception is the /children key for parents like
shows and seasons."* So a Show/Season's own `key` field points at its
`/children` listing (confirmed by Plex's own example responses), while its
`parentKey`/`grandparentKey` point at the plain metadata endpoint for the
parent/grandparent itself. `Mapper._own_key` handles this automatically
based on `metadata_type` - no source-side changes needed.

## Configuration reference

See `app/helper/config.py` for the full list and `.env.example` for a
ready-to-copy starting point.

## Shared ratingKey namespace

`GET /metadata/<ratingKey>` carries no type information. This
template tries every enabled category's clients, concatenated in a fixed
order (movie, show, season, episode, music — see
`app/routes.py`'s `_get_combined_search_service`). If two sources' ids
collide, the first category in that order wins.

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

Tests run against `TestConfig` (`app/helper/config.py`), which pins every
setting to its documented default regardless of a local `.env`.
