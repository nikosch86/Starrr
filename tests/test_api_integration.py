from unittest.mock import patch, Mock
from app import get_shows_from_api


def test_get_shows_from_api_success():
    mock_people_response = Mock()
    mock_people_response.status_code = 200
    mock_people_response.json.return_value = [
        {"person": {"id": 123, "name": "Bryan Cranston"}}
    ]

    mock_credits_response = Mock()
    mock_credits_response.status_code = 200
    mock_credits_response.json.return_value = [
        {
            "_embedded": {
                "show": {
                    "id": 169,
                    "name": "Breaking Bad",
                    "type": "Scripted",
                    "genres": ["Drama", "Crime", "Thriller"],
                    "externals": {
                        "tvrage": 18164,
                        "thetvdb": 81189,
                        "imdb": "tt0903747",
                    },
                }
            }
        },
        {
            "_embedded": {
                "show": {
                    "id": 249,
                    "name": "Malcolm in the Middle",
                    "type": "Scripted",
                    "genres": ["Comedy", "Family"],
                    "externals": {
                        "tvrage": 3838,
                        "thetvdb": 73838,
                        "imdb": "tt0212671",
                    },
                }
            }
        },
    ]

    with patch("app.api_session.get") as mock_get:
        mock_get.side_effect = [mock_people_response, mock_credits_response]
        result = get_shows_from_api("Bryan Cranston")

        expected = [{"tvdbId": "81189"}, {"tvdbId": "73838"}]
        assert result == expected
        assert mock_get.call_count == 2
        assert "Bryan%20Cranston" in mock_get.call_args_list[0][0][0]


def test_get_shows_from_api_filters_tv_shows_only():
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
        },
        {
            "_embedded": {
                "show": {
                    "name": "Godzilla",
                    "type": "Movie",
                    "externals": {"thetvdb": 999999},
                }
            }
        },
        {
            "_embedded": {
                "show": {
                    "name": "Better Call Saul",
                    "type": "Scripted",
                    "externals": {"thetvdb": 273181},
                }
            }
        },
    ]

    with patch("app.api_session.get") as mock_get:
        mock_get.side_effect = [mock_people_response, mock_credits_response]
        result = get_shows_from_api("Bryan Cranston")

        expected = [{"tvdbId": "81189"}, {"tvdbId": "273181"}]
        assert result == expected
        assert len(result) == 2


def test_get_shows_from_api_handles_empty_results():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch("app.api_session.get", return_value=mock_response):
        result = get_shows_from_api("Unknown Actor")

        assert result == []


def test_get_shows_from_api_handles_api_error():
    mock_response = Mock()
    mock_response.status_code = 500

    with patch("app.api_session.get", return_value=mock_response):
        result = get_shows_from_api("Bryan Cranston")

        assert result == []


def test_get_shows_from_api_handles_network_error():
    with patch("app.api_session.get", side_effect=Exception("Network error")):
        result = get_shows_from_api("Bryan Cranston")

        assert result == []


def test_get_shows_from_api_handles_no_person_found():
    mock_people_response = Mock()
    mock_people_response.status_code = 200
    mock_people_response.json.return_value = []

    with patch("requests.get", return_value=mock_people_response):
        result = get_shows_from_api("Nonexistent Person")

        assert result == []


def test_actor_name_normalization():
    """Test that actor names are normalized correctly for API calls"""
    mock_people_response = Mock()
    mock_people_response.status_code = 200
    mock_people_response.json.return_value = [
        {"person": {"id": 123, "name": "Bryan Cranston"}}
    ]

    mock_credits_response = Mock()
    mock_credits_response.status_code = 200
    mock_credits_response.json.return_value = []

    with patch("app.api_session.get") as mock_get:
        mock_get.side_effect = [mock_people_response, mock_credits_response]

        get_shows_from_api("bryan-cranston")

        first_call = mock_get.call_args_list[0]
        assert "bryan%20cranston" in first_call[0][0]


def test_get_shows_from_api_handles_missing_tvdb_id():
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
        },
        {
            "_embedded": {
                "show": {
                    "name": "Show Without TVDB",
                    "type": "Scripted",
                    "externals": {"imdb": "tt1234567"},
                }
            }
        },
        {
            "_embedded": {
                "show": {
                    "name": "Show Without Externals",
                    "type": "Scripted",
                }
            }
        },
    ]

    with patch("app.api_session.get") as mock_get:
        mock_get.side_effect = [mock_people_response, mock_credits_response]
        result = get_shows_from_api("Actor Name")

        expected = [{"tvdbId": "81189"}]
        assert result == expected
