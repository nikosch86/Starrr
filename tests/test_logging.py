import pytest
from unittest.mock import patch, Mock
import logging
import os
from app import app, get_shows_from_api_with_cache, setup_logging


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_logging_setup_from_env_variable():
    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
        logger = setup_logging()
        assert logger.level == logging.DEBUG

    with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}):
        logger = setup_logging()
        assert logger.level == logging.INFO

    with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
        logger = setup_logging()
        assert logger.level == logging.WARNING


def test_logging_defaults_to_info():
    with patch.dict(os.environ, {}, clear=True):
        logger = setup_logging()
        assert logger.level == logging.INFO


def test_debug_logging_for_api_calls():
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
                    "name": "Test Show",
                    "type": "Scripted",
                    "externals": {"thetvdb": 12345},
                }
            }
        }
    ]

    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
        setup_logging()

        with patch("app.logger") as mock_logger:
            with patch("app.api_session.get") as mock_get:
                mock_get.side_effect = [mock_people_response, mock_credits_response]
                get_shows_from_api_with_cache("Test Actor Debug")

                mock_logger.debug.assert_any_call(
                    "Searching for actor: Test Actor Debug (original: Test Actor Debug)"
                )
                mock_logger.debug.assert_any_call(
                    "Found person ID: 123 for Test Actor Debug"
                )
                assert mock_logger.debug.call_count >= 4


def test_info_logging_for_cache_operations():
    from app import _cache, _cache_timestamps

    _cache.clear()
    _cache_timestamps.clear()

    mock_people_response = Mock()
    mock_people_response.status_code = 200
    mock_people_response.json.return_value = [{"person": {"id": 123}}]

    mock_credits_response = Mock()
    mock_credits_response.status_code = 200
    mock_credits_response.json.return_value = []

    with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}):
        setup_logging()

        with patch("app.logger") as mock_logger:
            with patch("app.api_session.get") as mock_get:
                mock_get.side_effect = [mock_people_response, mock_credits_response]

                get_shows_from_api_with_cache("Cached Actor")
                mock_logger.info.assert_called_with(
                    "Cache miss for actor: cached actor"
                )

                mock_logger.reset_mock()

                get_shows_from_api_with_cache("Cached Actor")
                mock_logger.info.assert_called_with("Cache hit for actor: cached actor")


def test_error_logging_for_api_failures():
    with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
        setup_logging()

        with patch("app.logger") as mock_logger:
            with patch("app.api_session.get", side_effect=Exception("Network error")):
                result = get_shows_from_api_with_cache("Error Actor")

                assert result == []
                mock_logger.error.assert_called_with(
                    "Unexpected error fetching shows for Error Actor: Network error"
                )


def test_warning_logging_for_no_person_found():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
        setup_logging()

        with patch("app.logger") as mock_logger:
            with patch("requests.get", return_value=mock_response):
                result = get_shows_from_api_with_cache("Unknown Actor")

                assert result == []
                mock_logger.warning.assert_called_with(
                    "No person found for actor: Unknown Actor"
                )


def test_endpoint_logging(client):
    with patch("app.logger") as mock_logger:
        with patch("app.get_shows_from_api_with_cache") as mock_cache:
            mock_cache.return_value = [{"tvdbId": "81189"}, {"tvdbId": "73838"}]

            response = client.get("/shows/bryan-cranston")

            assert response.status_code == 200
            mock_logger.info.assert_any_call(
                "Request received for actor: bryan-cranston"
            )
            assert any(
                "Returning" in str(call_args)
                and "shows for bryan-cranston" in str(call_args)
                for call_args in mock_logger.info.call_args_list
            )
