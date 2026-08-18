"""
Integration tests for the example movie/show sources, using respx to mock
their upstream APIs.
"""
import httpx
import respx

from app import create_app
from app.helper.config import TestConfig


def _client():
    app = create_app(TestConfig)
    app.testing = True
    return app.test_client()


FILM = {
    "id": "2baf70d1-42bb-4437-b551-e5fed5a87abe",
    "title": "Spirited Away",
    "description": "A girl wanders into a spirit world.",
    "director": "Hayao Miyazaki",
    "producer": "Toshio Suzuki",
    "release_date": "2001",
    "running_time": "125",
    "rt_score": "97",
    "image": "https://example.com/poster.jpg",
    "movie_banner": "https://example.com/banner.jpg",
}

SHOWS = [{"score": 10, "show": {
    "id": 1, "name": "Archer", "premiered": "2009-09-17",
    "summary": "<p>A spy comedy.</p>", "averageRuntime": 22,
    "image": {"original": "https://example.com/archer.jpg"},
    "genres": ["Comedy", "Action"],
    "network": {"name": "FXX"},
    "rating": {"average": 8.4},
    "externals": {"imdb": "tt1486217", "thetvdb": 110381},
}}]


def test_movie_match_round_trip():
    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://ghibliapi.vercel.app/films").mock(return_value=httpx.Response(200, json=[FILM]))

        resp = _client().post("/library/metadata/matches", json={"type": 1, "title": "Spirited Away"})

    assert resp.status_code == 200
    metadata = resp.get_json()["MediaContainer"]["Metadata"]
    assert len(metadata) == 1
    assert metadata[0]["title"] == "Spirited Away"
    assert metadata[0]["type"] == "movie"
    assert metadata[0]["ratingKey"] == FILM["id"]
    assert metadata[0]["guid"] == f"{TestConfig.PROVIDER_IDENTIFIER}://movie/{FILM['id']}"


def test_movie_full_metadata_round_trip():
    with respx.mock(assert_all_called=True) as mock:
        mock.get(f"https://ghibliapi.vercel.app/films/{FILM['id']}").mock(
            return_value=httpx.Response(200, json=FILM)
        )

        resp = _client().get(f"/library/metadata/{FILM['id']}")

    assert resp.status_code == 200
    metadata = resp.get_json()["MediaContainer"]["Metadata"][0]
    assert metadata["studio"] == "Studio Ghibli"
    assert metadata["Director"] == [{"tag": "Hayao Miyazaki", "role": "Director"}]
    assert metadata["duration"] == 125 * 60_000
    assert metadata["year"] == 2001


def test_show_match_round_trip():
    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://api.tvmaze.com/search/shows", params={"q": "archer"}).mock(
            return_value=httpx.Response(200, json=SHOWS)
        )

        resp = _client().post("/library/metadata/matches", json={"type": 2, "title": "archer"})

    assert resp.status_code == 200
    metadata = resp.get_json()["MediaContainer"]["Metadata"]
    assert len(metadata) == 1
    assert metadata[0]["title"] == "Archer"
    assert metadata[0]["type"] == "show"
    assert metadata[0]["guid"] == f"{TestConfig.PROVIDER_IDENTIFIER}://show/1"


def test_movie_type_request_does_not_hit_show_source():
    """A movie-typed request should only call the movie category's source."""
    with respx.mock(assert_all_called=False) as mock:
        movie_route = mock.get("https://ghibliapi.vercel.app/films").mock(
            return_value=httpx.Response(200, json=[FILM])
        )
        show_route = mock.get("https://api.tvmaze.com/search/shows").mock(
            return_value=httpx.Response(200, json=[])
        )

        resp = _client().post("/library/metadata/matches", json={"type": 1, "title": "Spirited Away"})

    assert resp.status_code == 200
    assert movie_route.called
    assert not show_route.called
