"""
Example MOVIE source: the free, keyless Studio Ghibli API
(https://ghibliapi.vercel.app). Swap this for TMDB, OMDb, a private
catalog, or anything else that fits the SourceClient contract
(app/client/base.py); see app/client/registry.py for the registration
convention.

The API has no free-text search endpoint - it returns the whole film list -
so this source fetches it and filters/scores it locally using
``ignore_score``. A source whose upstream does its own server-side search
(e.g. app/client/source/show/example_show.py) doesn't need this step.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.client.base import ImageEntry, PersonEntry, RatingEntry, SourceMetadata, SourceUnavailableError
from app.schema.plex import MetadataType
from app.util.scoring import title_match_score

logger = logging.getLogger(__name__)


class ExampleMovieError(SourceUnavailableError):
    """Raised when the Ghibli API can't be reached or returns bad data."""


@dataclass
class ExampleMovieConfig:
    base_url: str = "https://ghibliapi.vercel.app"
    timeout: float = 10.0
    user_agent: str = "MediaProviderTemplate/1.0"


class ExampleMovie:
    """SourceClient for the Studio Ghibli API's /films endpoint."""

    name = "example_movie"

    def __init__(self, config: ExampleMovieConfig | None = None, client: httpx.Client | None = None):
        self.config = config or ExampleMovieConfig()
        self.client = client or httpx.Client()

    # ------------------------------------------------------------------
    # SourceClient interface
    # ------------------------------------------------------------------
    def search(
        self, query: str, ignore_score: int, skip: int = 0, genre: str | None = None
    ) -> list[SourceMetadata]:
        """GET /films (the whole catalog - no server-side search), scored
        locally against ``query`` and filtered to whatever clears
        ``ignore_score``, translated to SourceMetadata."""
        logger.debug(f"Searching Ghibli API for {query}")
        films = self._get("/films")
        if not isinstance(films, list):
            raise ExampleMovieError("Unexpected /films response shape: expected a list")

        scored = [(film, title_match_score(query, film.get("title") or "")) for film in films]
        matches = [film for film, score in scored if score >= ignore_score]
        return [self._to_normalized(film) for film in matches[skip:]]

    def get_entry(self, rating_key: str) -> SourceMetadata | None:
        """GET /films/{id}, translated to SourceMetadata, or None if not found."""
        try:
            film = self._get(f"/films/{rating_key}")
        except ExampleMovieError:
            return None
        if not isinstance(film, dict) or "id" not in film:
            return None
        return self._to_normalized(film)

    # ------------------------------------------------------------------
    # Raw HTTP mechanics
    # ------------------------------------------------------------------
    def _get(self, path: str) -> Any:
        url = f"{self.config.base_url.rstrip('/')}{path}"
        try:
            resp = self.client.get(
                url,
                headers={"User-Agent": self.config.user_agent, "Accept": "application/json"},
                timeout=self.config.timeout,
            )
        except httpx.RequestError as exc:
            logger.error("Request to %s failed: %s", url, exc, exc_info=True)
            raise ExampleMovieError(f"Failed to reach Ghibli API at {url}: {exc}") from exc

        if resp.status_code == 404:
            raise ExampleMovieError(f"{url} returned 404")

        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("Ghibli API returned an error for %s: %s", url, exc, exc_info=True)
            raise ExampleMovieError(f"Ghibli API error for {url}: {exc}") from exc

        try:
            return resp.json()
        except ValueError as exc:
            raise ExampleMovieError(f"Ghibli API returned non-JSON response for {url}") from exc

    # ------------------------------------------------------------------
    # Translation to SourceMetadata
    # ------------------------------------------------------------------
    @staticmethod
    def _to_normalized(film: dict[str, Any]) -> SourceMetadata:
        entry = SourceMetadata(
            upstream_id=str(film["id"]),
            title=film.get("title") or "",
            metadata_type=MetadataType.MOVIE,
            originally_available_at=f"{film['release_date']}-01-01" if film.get("release_date") else None,
            year=int(film["release_date"]) if str(film.get("release_date") or "").isdigit() else None,
            summary=(film.get("description") or "").strip() or None,
            original_title=film.get("original_title") or None,
            studio="Studio Ghibli",
            studios=["Studio Ghibli"],
        )

        running_time = film.get("running_time")
        if running_time and str(running_time).isdigit():
            entry.duration_ms = int(running_time) * 60_000

        image = film.get("image")
        if image:
            entry.thumb = image
            entry.images = [ImageEntry(type="coverPoster", url=image, alt=entry.title)]
        banner = film.get("movie_banner")
        if banner:
            entry.art = banner
            entry.images.append(ImageEntry(type="background", url=banner, alt=entry.title))

        director = film.get("director")
        if director:
            entry.directors = [PersonEntry(tag=director, role="Director")]
        producer = film.get("producer")
        if producer:
            entry.producers = [PersonEntry(tag=producer, role="Producer")]

        rt_score = film.get("rt_score")
        if rt_score and str(rt_score).isdigit():
            entry.ratings = [
                RatingEntry(image="rottentomatoes://image.rating.ripe", type="critic", value=round(int(rt_score) / 10, 1))
            ]

        return entry
