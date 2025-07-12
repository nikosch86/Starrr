# Starrr - TV Shows by Actor for Sonarr

A microservice that enables Sonarr to automatically track TV shows featuring specific actors, similar to how Radarr uses TMDB Person lists for movies.

## How It Works

Starrr provides TVDB IDs for all TV shows featuring a given actor, which Sonarr can import via custom lists:

1. **In Sonarr**: Settings → Import Lists → Add List → Custom List
2. **List URL**: `http://starrr:8000/shows/bryan-cranston`
3. Sonarr will automatically add Breaking Bad, Malcolm in the Middle, and any future Bryan Cranston shows

## Features

- **Sonarr Compatible**: Returns TVDB IDs in the format Sonarr expects
- **1-hour cache**: Reduces API calls to TVMaze
- **API Documentation**: Swagger UI at `/docs`

## Quick Start

### Docker Compose with Sonarr

See `docker-compose.example.yml` for a complete setup. Key configuration:

```yaml
services:
  sonarr:
    image: lscr.io/linuxserver/sonarr:latest
    ports:
      - 8989:8989
  
  starrr:
    image: ghcr.io/yourusername/starrr:latest
```

### Local Development

```bash
make install
make run
```

## API Usage

```bash
# Get Bryan Cranston shows
curl http://localhost:8000/shows/bryan-cranston
# [{"tvdbId":"81189"},{"tvdbId":"73838"}]

# Jean-Claude Van Damme shows
curl http://localhost:8000/shows/Jean-Claude%20Van%20Damme
# [{"tvdbId":"123456"}]
```

## Configuration

- `LOG_LEVEL`: Set logging detail (DEBUG, INFO, WARNING, ERROR)

## Development

Quality checks are enforced via GitHub Actions and can be run locally:

```bash
make check    # Run linting, type checking, and tests
make all      # Run everything including coverage (must be >95%)
```

Individual commands:
```bash
make lint      # Code style checks with ruff
make typecheck # Type checking with mypy
make test      # Run test suite
make coverage  # Generate coverage report (97% coverage)
make format    # Auto-format code
```

## Credits

Powered by the free [TVMaze API](https://www.tvmaze.com/api) - please respect their terms of service.

## License

MIT