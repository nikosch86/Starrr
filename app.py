from flask import Flask
from flask_restx import Api, Resource, fields
import requests
from urllib.parse import quote
import time
import logging
import os
import re
from typing import List, Dict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)

# Configure Flask-RESTX for API documentation
api = Api(
    app,
    version="1.0",
    title="Starrr API",
    description="A service to discover TV shows by actor, designed to complement Sonarr in the *arr ecosystem",
    doc="/docs",
)

# Define namespaces
shows_ns = api.namespace("shows", description="TV show operations")
health_ns = api.namespace("health", description="Health check")

# Define models for API documentation
show_model = api.model(
    "Show",
    {"tvdbId": fields.String(required=True, description="The TVDB ID of the show")},
)

error_model = api.model(
    "Error", {"error": fields.String(required=True, description="Error message")}
)

# Cache timeout in seconds (1 hour)
CACHE_TIMEOUT = 3600
# Maximum cache size to prevent memory exhaustion
MAX_CACHE_SIZE = 1000
# Request timeout in seconds
REQUEST_TIMEOUT = 10


def setup_logging():
    """Set up logging configuration based on environment variable"""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # Force reconfiguration
    )

    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    return logger


# Initialize logger
logger = setup_logging()

# Simple time-based cache
_cache: Dict[str, List[Dict[str, str]]] = {}
_cache_timestamps: Dict[str, float] = {}


def create_session() -> requests.Session:
    """Create a requests session with retry logic"""
    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1,
        respect_retry_after_header=True,
        raise_on_status=True,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


# Create a global session for reuse
api_session = create_session()


def validate_actor_name(actor_name: str) -> bool:
    """Validate actor name input"""
    if not actor_name or len(actor_name) > 100:
        return False

    if not re.match(r"^[a-zA-Z0-9\s\-''.]+$", actor_name):
        return False

    return True


def normalize_actor_name(actor_name: str) -> str:
    """Normalize actor name for TVMaze API"""
    if " " not in actor_name and "-" in actor_name:
        return actor_name.replace("-", " ")
    return actor_name


def evict_oldest_cache_entry():
    """Remove the oldest cache entry"""
    if _cache and _cache_timestamps:
        oldest_key = min(_cache_timestamps, key=_cache_timestamps.get)
        del _cache[oldest_key]
        del _cache_timestamps[oldest_key]
        logger.debug(f"Evicted oldest cache entry: {oldest_key}")


def get_shows_from_api_with_cache(actor_name: str) -> List[Dict[str, str]]:
    """Fetch TV shows for an actor from TVMaze API with caching"""
    cache_key = actor_name.lower()
    if cache_key in _cache:
        if time.time() - _cache_timestamps[cache_key] < CACHE_TIMEOUT:
            logger.info(f"Cache hit for actor: {cache_key}")
            return _cache[cache_key]

    logger.info(f"Cache miss for actor: {cache_key}")
    shows = get_shows_from_api(actor_name)

    if len(_cache) >= MAX_CACHE_SIZE:
        evict_oldest_cache_entry()

    _cache[cache_key] = shows
    _cache_timestamps[cache_key] = time.time()

    return shows


def get_shows_from_api(actor_name: str) -> List[Dict[str, str]]:
    """Fetch TV shows for an actor from TVMaze API"""
    try:
        normalized_name = normalize_actor_name(actor_name)
        logger.debug(f"Searching for actor: {normalized_name} (original: {actor_name})")
        url = f"https://api.tvmaze.com/search/people?q={quote(normalized_name)}"
        response = api_session.get(url, timeout=REQUEST_TIMEOUT)

        people_data = response.json()
        if not people_data:
            logger.warning(f"No person found for actor: {actor_name}")
            return []

        person_id = people_data[0]["person"]["id"]
        logger.debug(f"Found person ID: {person_id} for {actor_name}")

        credits_url = (
            f"https://api.tvmaze.com/people/{person_id}/castcredits?embed=show"
        )
        logger.debug(f"Fetching cast credits from: {credits_url}")
        credits_response = api_session.get(credits_url, timeout=REQUEST_TIMEOUT)

        credits_data = credits_response.json()

        shows = []
        seen_tvdb_ids = set()

        for credit in credits_data:
            show = credit.get("_embedded", {}).get("show", {})
            show_type = show.get("type", "")
            show_name = show.get("name", "")

            externals = show.get("externals", {})
            tvdb_id = externals.get("thetvdb")

            if tvdb_id and show_type in [
                "Scripted",
                "Reality",
                "Talk Show",
                "Game Show",
                "Documentary",
                "Animation",
            ]:
                tvdb_id_str = str(tvdb_id)
                if tvdb_id_str not in seen_tvdb_ids:
                    seen_tvdb_ids.add(tvdb_id_str)
                    shows.append({"tvdbId": tvdb_id_str})
                    logger.debug(f"Added show: {show_name} (TVDB: {tvdb_id_str})")

        logger.debug(f"Found {len(shows)} TV shows with TVDB IDs for {actor_name}")
        return shows

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching shows for {actor_name}: {str(e)}")
        return []
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout fetching shows for {actor_name}: {str(e)}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching shows for {actor_name}: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching shows for {actor_name}: {str(e)}")
        return []


@health_ns.route("")
class HealthCheck(Resource):
    @api.doc("health_check")
    @api.response(200, "Service is healthy")
    def get(self):
        """Health check endpoint for container orchestration"""
        return {"status": "healthy"}, 200


@shows_ns.route("/<string:actor_name>")
@shows_ns.param("actor_name", "The name of the actor to search for")
class ShowsByActor(Resource):
    @api.doc("get_shows_by_actor")
    @api.response(200, "Success", [show_model])
    @api.response(400, "Invalid actor name", error_model)
    @api.response(500, "Internal server error")
    def get(self, actor_name: str):
        """Get TV shows featuring a specific actor

        Returns a list of TVDB IDs for TV shows featuring the specified actor.
        This endpoint is designed to work like TVDB Person lists for Radarr,
        enabling automatic tracking of TV shows with specific actors in Sonarr.

        The results are cached for 1 hour to reduce API calls to TVMaze.
        """
        logger.info(f"Request received for actor: {actor_name}")

        if not validate_actor_name(actor_name):
            logger.warning(f"Invalid actor name: {actor_name}")
            return {
                "error": "Invalid actor name. Must be 1-100 characters, alphanumeric with spaces, hyphens, apostrophes, and periods only."
            }, 400

        shows = get_shows_from_api_with_cache(actor_name)

        logger.info(f"Returning {len(shows)} shows for {actor_name}")
        return shows


if __name__ == "__main__":
    app.run(debug=True)
