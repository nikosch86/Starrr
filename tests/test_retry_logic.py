from unittest.mock import patch, Mock
from app import get_shows_from_api, api_session
import requests


def test_retry_on_server_error():
    """Test that the API handles 5xx errors gracefully"""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.reason = "Internal Server Error"
    mock_response.text = '{"error": "Server Error"}'

    error = requests.HTTPError("500 Server Error")
    error.response = mock_response

    with patch("app.api_session.get") as mock_get:
        mock_get.side_effect = error

        result = get_shows_from_api("Test Actor")

        assert result == []
        assert mock_get.call_count == 1


def test_retry_on_rate_limit():
    """Test that the API handles 429 rate limit errors gracefully"""
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.reason = "Too Many Requests"
    mock_response.text = '{"error": "Rate Limited"}'

    error = requests.HTTPError("429 Too Many Requests")
    error.response = mock_response

    with patch("app.api_session.get") as mock_get:
        mock_get.side_effect = error

        result = get_shows_from_api("Rate Limited Actor")

        assert result == []
        assert mock_get.call_count == 1


def test_max_retries_exceeded():
    """Test that we handle persistent errors gracefully"""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.reason = "Internal Server Error"
    mock_response.text = '{"error": "Server Error"}'

    error = requests.HTTPError("500 Server Error")
    error.response = mock_response

    with patch("app.api_session.get") as mock_get:
        mock_get.side_effect = error

        result = get_shows_from_api("Always Failing Actor")

        assert result == []
        assert mock_get.call_count == 1


def test_no_retry_on_client_error():
    """Test that we don't retry on 4xx errors (except 429)"""
    mock_response_404 = Mock()
    mock_response_404.status_code = 404

    with patch("app.api_session.get") as mock_get:
        mock_get.return_value = mock_response_404

        result = get_shows_from_api("Not Found Actor")

        assert mock_get.call_count == 1
        assert result == []


def test_retry_configuration():
    """Test that the retry mechanism is properly configured"""
    adapter = api_session.get_adapter("https://api.tvmaze.com")
    retry = adapter.max_retries

    assert retry.total == 3
    assert 429 in retry.status_forcelist
    assert 500 in retry.status_forcelist
    assert 502 in retry.status_forcelist
    assert 503 in retry.status_forcelist
    assert 504 in retry.status_forcelist
    assert retry.backoff_factor == 1
    assert retry.respect_retry_after_header is True
    assert retry.raise_on_status is True

    assert "GET" in retry.allowed_methods
    assert "HEAD" in retry.allowed_methods
    assert "OPTIONS" in retry.allowed_methods
