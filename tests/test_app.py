import pytest
from unittest.mock import patch
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_shows_endpoint_exists(client):
    response = client.get("/shows/bryan-cranston")
    assert response.status_code == 200


def test_shows_endpoint_returns_json(client):
    with patch("app.get_shows_from_api_with_cache") as mock_cache:
        mock_cache.return_value = [{"tvdbId": "81189"}]

        response = client.get("/shows/bryan-cranston")
        assert response.content_type == "application/json"


def test_shows_endpoint_returns_list(client):
    with patch("app.get_shows_from_api_with_cache") as mock_cache:
        mock_cache.return_value = [{"tvdbId": "81189"}]

        response = client.get("/shows/bryan-cranston")
        data = response.get_json()
        assert isinstance(data, list)


def test_bryan_cranston_shows(client):
    with patch("app.get_shows_from_api_with_cache") as mock_cache:
        mock_cache.return_value = [
            {"tvdbId": "81189"},  # Breaking Bad
            {"tvdbId": "73838"},  # Malcolm in the Middle
            {"tvdbId": "366811"},  # Your Honor
        ]

        response = client.get("/shows/bryan-cranston")
        data = response.get_json()

        # Check that we get TVDB IDs in the response
        assert len(data) == 3
        assert {"tvdbId": "81189"} in data
        assert {"tvdbId": "73838"} in data
        mock_cache.assert_called_once_with("bryan-cranston")


def test_unknown_actor_returns_empty_list(client):
    with patch("app.get_shows_from_api_with_cache") as mock_cache:
        mock_cache.return_value = []

        response = client.get("/shows/unknown-actor")
        data = response.get_json()
        assert data == []
        assert response.status_code == 200
        mock_cache.assert_called_once_with("unknown-actor")


def test_actor_name_case_insensitive(client):
    with patch("app.get_shows_from_api_with_cache") as mock_cache:
        mock_cache.return_value = [
            {"tvdbId": "73244"},  # The Office
            {"tvdbId": "359260"},  # The Morning Show
            {"tvdbId": "377513"},  # Space Force
        ]

        response_lower = client.get("/shows/steve-carell")
        response_upper = client.get("/shows/STEVE-CARELL")
        response_mixed = client.get("/shows/Steve-Carell")

        expected = [
            {"tvdbId": "73244"},
            {"tvdbId": "359260"},
            {"tvdbId": "377513"},
        ]

        # All should return the same data
        assert response_lower.get_json() == expected
        assert response_upper.get_json() == expected
        assert response_mixed.get_json() == expected

        # Check all variations were called
        assert mock_cache.call_count == 3


def test_shows_endpoint_uses_api_for_all_actors(client):
    with patch("app.get_shows_from_api_with_cache") as mock_cache:
        mock_cache.return_value = [
            {"tvdbId": "311714"},  # The Good Place
            {"tvdbId": "77623"},  # Cheers
        ]

        response = client.get("/shows/ted-danson")
        data = response.get_json()

        assert response.status_code == 200
        assert data == [
            {"tvdbId": "311714"},
            {"tvdbId": "77623"},
        ]
        mock_cache.assert_called_once_with("ted-danson")


def test_invalid_actor_name_with_special_characters(client):
    """Test that actor names with invalid special characters are rejected"""
    response = client.get("/shows/actor@example.com")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Invalid actor name" in data["error"]


def test_invalid_actor_name_too_long(client):
    """Test that actor names longer than 100 characters are rejected"""
    long_name = "a" * 101
    response = client.get(f"/shows/{long_name}")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Invalid actor name" in data["error"]


def test_invalid_actor_name_empty(client):
    """Test that empty actor names are rejected"""
    response = client.get("/shows/")
    assert response.status_code == 404  # Flask returns 404 for empty path segment


def test_valid_actor_names_with_allowed_characters(client):
    """Test that actor names with apostrophes, hyphens, and periods are accepted"""
    with patch("app.get_shows_from_api_with_cache") as mock_cache:
        mock_cache.return_value = [{"tvdbId": "123456"}]

        # Test various valid names
        valid_names = [
            "Scarlett O'Hara",
            "Jean-Claude Van Damme",
            "Samuel L. Jackson",
            "Mary-Kate Olsen",
            "Robert Downey Jr.",
        ]

        for name in valid_names:
            response = client.get(f"/shows/{name}")
            assert response.status_code == 200
            data = response.get_json()
            assert isinstance(data, list)
