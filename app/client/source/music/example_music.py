"""
Example MUSIC source: the free, keyless MusicBrainz API
(https://musicbrainz.org/doc/MusicBrainz_API).

Note: Plex's custom-provider API currently documents support for only
movie/show/season/episode - music libraries aren't supported yet. This
source is forward-looking scaffolding, off by default
(Config.ENABLE_MUSIC_SOURCES).

MusicBrainz requires a descriptive User-Agent (see
``ExampleMusicConfig.user_agent``) and asks for no more than ~1
request/second sustained.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.client.base import SourceMetadata, SourceUnavailableError
from app.schema.plex import METADATA_TYPE_ARTIST

logger = logging.getLogger(__name__)


class ExampleMusicError(SourceUnavailableError):
    """Raised when MusicBrainz can't be reached or returns bad data."""


@dataclass
class ExampleMusicConfig:
    base_url: str = "https://musicbrainz.org/ws/2"
    timeout: float = 10.0
    user_agent: str = "MediaProviderTemplate/1.0 ( set a contact URL/email per MusicBrainz's API etiquette )"


class ExampleMusic:
    """SourceClient for MusicBrainz's /artist endpoints. Only produces
    "artist" entries - album/track are natural extensions (MusicBrainz's
    /release-group and /recording endpoints)."""

    name = "example_music"

    def __init__(self, config: ExampleMusicConfig | None = None, client: httpx.Client | None = None):
        self.config = config or ExampleMusicConfig()
        self.client = client or httpx.Client()

    # ------------------------------------------------------------------
    # SourceClient interface
    # ------------------------------------------------------------------
    def search(
        self, query: str, ignore_score: int, skip: int = 0, genre: str | None = None
    ) -> list[SourceMetadata]:
        """GET /artist?query=..., translated to SourceMetadata. MusicBrainz
        returns its own 0-100 relevance ``score`` per result, which is used
        directly against ``ignore_score`` rather than re-scoring locally."""
        payload = self._get("/artist", params={"query": query, "fmt": "json"})
        artists = payload.get("artists") if isinstance(payload, dict) else None
        if artists is None:
            raise ExampleMusicError("Unexpected /artist response shape: missing 'artists' array")

        matches = [a for a in artists if int(a.get("score", 0)) >= ignore_score]
        return [self._to_normalized(a) for a in matches[skip:]]

    def get_entry(self, rating_key: str) -> SourceMetadata | None:
        """GET /artist/{mbid}, translated to SourceMetadata, or None if
        not found. MusicBrainz IDs are UUIDs, which already satisfy Plex's
        ratingKey character rules ([a-zA-Z0-9_-]) with no rewriting needed."""
        try:
            artist = self._get(f"/artist/{rating_key}", params={"fmt": "json", "inc": "tags"})
        except ExampleMusicError:
            return None
        if not isinstance(artist, dict) or "id" not in artist:
            return None
        return self._to_normalized(artist)

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
            raise ExampleMusicError(f"Failed to reach MusicBrainz at {url}: {exc}") from exc

        if resp.status_code == 404:
            raise ExampleMusicError(f"{url} returned 404")

        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("MusicBrainz returned an error for %s: %s", url, exc, exc_info=True)
            raise ExampleMusicError(f"MusicBrainz API error for {url}: {exc}") from exc

        try:
            return resp.json()
        except ValueError as exc:
            raise ExampleMusicError(f"MusicBrainz returned non-JSON response for {url}") from exc

    # ------------------------------------------------------------------
    # Translation to SourceMetadata
    # ------------------------------------------------------------------
    @staticmethod
    def _to_normalized(artist: dict[str, Any]) -> SourceMetadata:
        life_span = artist.get("life-span") or {}
        entry = SourceMetadata(
            upstream_id=str(artist["id"]),
            title=artist.get("name") or "",
            metadata_type=METADATA_TYPE_ARTIST,
            originally_available_at=life_span.get("begin"),
            year=int(life_span["begin"][:4]) if life_span.get("begin", "")[:4].isdigit() else None,
            summary=artist.get("disambiguation") or None,
            countries=[artist["country"]] if artist.get("country") else [],
        )
        entry.genres = [t["name"] for t in (artist.get("tags") or []) if t.get("name")][:5]
        return entry
