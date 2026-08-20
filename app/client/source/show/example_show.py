"""
Example SHOW source: the free, keyless TVMaze API (https://www.tvmaze.com/api).
Swap this for TheTVDB, TMDB, a private catalog, etc; see
app/client/registry.py for the registration convention.

Only produces "show" entries (type=2). Season/episode are their own
categories (app/client/source/season/, .../episode/), each with their own
ENABLE_*/*_SOURCES config - both ship enabled with no default source. To
add one: fetch the child list, set
``metadata_type=MetadataType.SEASON``/``MetadataType.EPISODE`` (see
app/schema/plex.py), and populate ``parent_upstream_id``/``parent_title``/
``grandparent_*``/``index``/``parent_index`` the way this module populates
the top-level fields on a show.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.client.base import ImageEntry, SourceMetadata, RatingEntry, SourceUnavailableError
from app.schema.plex import MetadataType

logger = logging.getLogger(__name__)


class ExampleShowError(SourceUnavailableError):
    """Raised when TVMaze can't be reached or returns bad data."""


@dataclass
class ExampleShowConfig:
    base_url: str = "https://api.tvmaze.com"
    timeout: float = 10.0
    user_agent: str = "MediaProviderTemplate/1.0"


class ExampleShow:
    """SourceClient for TVMaze's /search/shows and /shows/{id} endpoints.
    TVMaze does its own full-text search server-side, so ``ignore_score``
    isn't used to pre-filter here."""

    name = "example_show"

    def __init__(self, config: ExampleShowConfig | None = None, client: httpx.Client | None = None):
        self.config = config or ExampleShowConfig()
        self.client = client or httpx.Client()

    # ------------------------------------------------------------------
    # SourceClient interface
    # ------------------------------------------------------------------
    def search(
        self, query: str, ignore_score: int, skip: int = 0, genre: str | None = None
    ) -> list[SourceMetadata]:
        """GET /search/shows?q=..., translated to SourceMetadata."""
        logger.debug(f"Searching TVMaze for {query}")
        payload = self._get("/search/shows", params={"q": query})
        if not isinstance(payload, list):
            raise ExampleShowError("Unexpected /search/shows response shape: expected a list")

        results = [item.get("show") for item in payload if isinstance(item, dict) and item.get("show")]
        return [self._to_normalized(show) for show in results[skip:]]

    def get_entry(self, rating_key: str) -> SourceMetadata | None:
        """GET /shows/{id}, translated to SourceMetadata, or None if not found."""
        try:
            show = self._get(f"/shows/{rating_key}")
        except ExampleShowError:
            return None
        if not isinstance(show, dict) or "id" not in show:
            return None
        return self._to_normalized(show)

    # ------------------------------------------------------------------
    # Raw HTTP mechanics
    # ------------------------------------------------------------------
    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.config.base_url.rstrip('/')}{path}"
        try:
            resp = self.client.get(
                url,
                params=params,
                headers={"User-Agent": self.config.user_agent, "Accept": "application/json"},
                timeout=self.config.timeout,
            )
        except httpx.RequestError as exc:
            logger.error("Request to %s failed: %s", url, exc, exc_info=True)
            raise ExampleShowError(f"Failed to reach TVMaze at {url}: {exc}") from exc

        if resp.status_code == 404:
            raise ExampleShowError(f"{url} returned 404")

        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("TVMaze returned an error for %s: %s", url, exc, exc_info=True)
            raise ExampleShowError(f"TVMaze API error for {url}: {exc}") from exc

        try:
            return resp.json()
        except ValueError as exc:
            raise ExampleShowError(f"TVMaze returned non-JSON response for {url}") from exc

    # ------------------------------------------------------------------
    # Translation to SourceMetadata
    # ------------------------------------------------------------------
    @staticmethod
    def _to_normalized(show: dict[str, Any]) -> SourceMetadata:
        entry = SourceMetadata(
            upstream_id=str(show["id"]),
            title=show.get("name") or "",
            metadata_type=MetadataType.SHOW,
            originally_available_at=show.get("premiered"),
            year=int(show["premiered"][:4]) if show.get("premiered") else None,
            summary=_strip_html(show.get("summary")),
        )

        runtime = show.get("averageRuntime") or show.get("runtime")
        if runtime:
            entry.duration_ms = int(runtime) * 60_000

        image = show.get("image") or {}
        thumb = image.get("original") or image.get("medium")
        if thumb:
            entry.thumb = thumb
            entry.images = [ImageEntry(type="coverPoster", url=thumb, alt=entry.title)]

        entry.genres = [g for g in (show.get("genres") or []) if g]

        network = (show.get("network") or show.get("webChannel") or {}).get("name")
        if network:
            entry.networks = [network]
            entry.studio = network

        rating = (show.get("rating") or {}).get("average")
        if rating is not None:
            entry.ratings = [RatingEntry(image="themoviedb://image.rating", type="audience", value=round(float(rating), 1))]

        externals = show.get("externals") or {}
        if externals.get("imdb"):
            entry.external_ids.append(f"imdb://{externals['imdb']}")
        if externals.get("thetvdb"):
            entry.external_ids.append(f"tvdb://{externals['thetvdb']}")

        return entry


def _strip_html(text: str | None) -> str | None:
    """TVMaze's `summary` is a short HTML fragment. Strip tags with a plain
    regex rather than pulling in an HTML parser dependency for one field."""
    if not text:
        return None
    import re

    stripped = re.sub(r"<[^>]+>", "", text).strip()
    return stripped or None
