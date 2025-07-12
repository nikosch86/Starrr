import pytest
from unittest.mock import patch, Mock
import time
from app import app, get_shows_from_api_with_cache


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_cache_prevents_repeated_api_calls():
    from app import _cache, _cache_timestamps

    _cache.clear()
    _cache_timestamps.clear()

    mock_people_response = Mock()
    mock_people_response.status_code = 200
    mock_people_response.json.return_value = [{"person": {"id": 123}}]

    mock_credits_response = Mock()
    mock_credits_response.status_code = 200
    mock_credits_response.json.return_value = [
        {
            "_embedded": {
                "show": {
                    "name": "Breaking Bad",
                    "type": "Scripted",
                    "externals": {"thetvdb": 81189},
                }
            }
        }
    ]

    with patch("app.api_session.get") as mock_get:
        mock_get.side_effect = [mock_people_response, mock_credits_response]

        result1 = get_shows_from_api_with_cache("Bryan Cranston")
        assert result1 == [{"tvdbId": "81189"}]
        assert mock_get.call_count == 2

        mock_get.reset_mock()

        result2 = get_shows_from_api_with_cache("Bryan Cranston")
        assert result2 == [{"tvdbId": "81189"}]
        assert mock_get.call_count == 0


def test_cache_expires_after_timeout():
    mock_people_response = Mock()
    mock_people_response.status_code = 200
    mock_people_response.json.return_value = [{"person": {"id": 123}}]

    mock_credits_response = Mock()
    mock_credits_response.status_code = 200
    mock_credits_response.json.return_value = [
        {
            "_embedded": {
                "show": {
                    "name": "Breaking Bad",
                    "type": "Scripted",
                    "externals": {"thetvdb": 81189},
                }
            }
        }
    ]

    with patch("app.api_session.get") as mock_get:
        with patch("app.CACHE_TIMEOUT", 0.1):
            mock_get.side_effect = [mock_people_response, mock_credits_response]

            get_shows_from_api_with_cache("Test Actor")
            assert mock_get.call_count == 2

            time.sleep(0.2)

            mock_get.reset_mock()
            mock_get.side_effect = [mock_people_response, mock_credits_response]

            get_shows_from_api_with_cache("Test Actor")
            assert mock_get.call_count == 2


def test_case_insensitive_caching():
    """Test that cache is case-insensitive"""
    from app import _cache, _cache_timestamps, get_shows_from_api_with_cache

    _cache.clear()
    _cache_timestamps.clear()

    mock_people_response = Mock()
    mock_people_response.status_code = 200
    mock_people_response.json.return_value = [{"person": {"id": 456}}]

    mock_credits_response = Mock()
    mock_credits_response.status_code = 200
    mock_credits_response.json.return_value = [
        {
            "_embedded": {
                "show": {
                    "name": "Action Show",
                    "type": "Scripted",
                    "externals": {"thetvdb": 99999},
                }
            }
        }
    ]

    with patch("app.api_session.get") as mock_get:
        mock_get.side_effect = [mock_people_response, mock_credits_response]

        result1 = get_shows_from_api_with_cache("Bryan Cranston")
        assert mock_get.call_count == 2

        mock_get.reset_mock()

        result2 = get_shows_from_api_with_cache("BRYAN CRANSTON")
        assert mock_get.call_count == 0

        assert result1 == result2
        assert result1 == [{"tvdbId": "99999"}]


def test_different_actors_cached_separately():
    mock_people_response1 = Mock()
    mock_people_response1.status_code = 200
    mock_people_response1.json.return_value = [{"person": {"id": 123}}]

    mock_credits_response1 = Mock()
    mock_credits_response1.status_code = 200
    mock_credits_response1.json.return_value = [
        {
            "_embedded": {
                "show": {
                    "name": "Show 1",
                    "type": "Scripted",
                    "externals": {"thetvdb": 111111},
                }
            }
        }
    ]

    mock_people_response2 = Mock()
    mock_people_response2.status_code = 200
    mock_people_response2.json.return_value = [{"person": {"id": 456}}]

    mock_credits_response2 = Mock()
    mock_credits_response2.status_code = 200
    mock_credits_response2.json.return_value = [
        {
            "_embedded": {
                "show": {
                    "name": "Show 2",
                    "type": "Scripted",
                    "externals": {"thetvdb": 222222},
                }
            }
        }
    ]

    with patch("app.api_session.get") as mock_get:
        mock_get.side_effect = [mock_people_response1, mock_credits_response1]
        result1 = get_shows_from_api_with_cache("Actor 1")
        assert result1 == [{"tvdbId": "111111"}]

        mock_get.side_effect = [mock_people_response2, mock_credits_response2]
        result2 = get_shows_from_api_with_cache("Actor 2")
        assert result2 == [{"tvdbId": "222222"}]

        assert mock_get.call_count == 4
