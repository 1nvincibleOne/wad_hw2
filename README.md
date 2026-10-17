# triplogger

A small REST API for recording trips and counting them by transport mode. Built
with Python, FastAPI, and PostgreSQL; runs as two Docker Compose services.

## Run

1. Start Docker Desktop with Linux containers.
2. Copy `.env.example` to `.env` and set `POSTGRES_PASSWORD` to a unique password.
3. Run `docker compose up --build`.
4. Open [API documentation](http://localhost:8000/docs) to try the endpoints.

`APP_PORT` in `.env` controls the host port (default: 8000). Database credentials
are also configured there. Keep `.env` out of Git.

## API

| Endpoint | Description |
| --- | --- |
| `POST /trips` | Record origin/destination coordinates, departure time, and transport mode |
| `GET /trips` | List matching trips, newest first |
| `GET /stats` | Count matching trips by transport mode |

Supported modes: `walk`, `bicycle`, `car`, `bus`. Timestamps must include a timezone
offset or `Z`; responses use UTC. The documentation includes an example request.

Both GET endpoints accept `mode`, `from_time` (inclusive), `to_time` (exclusive),
and an origin rectangle: `min_lat`, `max_lat`, `min_lon`, `max_lon`. Supply all four
rectangle bounds or none. Filters combine with AND; rectangle edges are included.

`GET /trips` accepts `limit` (default 100, maximum 500). Statistics count all
matching records. Empty results return `[]`; invalid input returns 422. The local
API uses a shared dataset without authentication.

## Persistence

PostgreSQL data lives in a named volume and survives `docker compose down` followed
by `docker compose up`. `docker compose down -v` deletes that data. Changing `.env`
credentials does not update an already initialized database.

## Tests

With the containers running, execute in PowerShell:

```powershell
Get-Content -Raw tests/test_api.py | docker compose exec -T backend python -
```

The integration tests use the real API and database and remove their own records.
