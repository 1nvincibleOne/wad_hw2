from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Literal

import psycopg
from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import (
    AfterValidator, AwareDatetime, BaseModel, BeforeValidator,
    ConfigDict, Field, model_validator,
)

import db

Latitude = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
Longitude = Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
Mode = Literal["walk", "bicycle", "car", "bus"]


def require_timestamp(value):
    if not isinstance(value, (str, datetime)) or (isinstance(value, str) and "T" not in value):
        raise ValueError("Use an ISO 8601 timestamp with T and an offset")
    return value


def use_utc(value: datetime) -> datetime:
    try:
        return value.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError("Timestamp is outside the supported UTC range") from exc


Timestamp = Annotated[AwareDatetime, BeforeValidator(require_timestamp), AfterValidator(use_utc)]


class TripInput(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {
        "origin_lat": 43.2389, "origin_lon": 76.8897,
        "destination_lat": 43.2500, "destination_lon": 76.9500,
        "departed_at": "2026-10-16T08:00:00+05:00", "transport_mode": "bus",
    }})
    origin_lat: Latitude
    origin_lon: Longitude
    destination_lat: Latitude
    destination_lon: Longitude
    departed_at: Timestamp
    transport_mode: Mode


class Trip(TripInput):
    id: int


class Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Mode | None = None
    from_time: Timestamp | None = Field(None, description="Departure start, inclusive.")
    to_time: Timestamp | None = Field(None, description="Departure end, exclusive.")
    min_lat: Latitude | None = Field(None, description="Origin rectangle: all four bounds required.")
    max_lat: Latitude | None = None
    min_lon: Longitude | None = None
    max_lon: Longitude | None = None

    @model_validator(mode="after")
    def check_bounds(self):
        if self.from_time is not None and self.to_time is not None:
            if self.from_time >= self.to_time:
                raise ValueError("from_time must be earlier than to_time")
        bounds = (self.min_lat, self.max_lat, self.min_lon, self.max_lon)
        if any(value is not None for value in bounds):
            if any(value is None for value in bounds):
                raise ValueError("Supply all four origin rectangle bounds")
            if self.min_lat > self.max_lat or self.min_lon > self.max_lon:
                raise ValueError("Rectangle minimums must not exceed maximums")
        return self


class ListFilters(Filters):
    limit: int = Field(100, ge=1, le=500)


class ModeCount(BaseModel):
    transport_mode: Mode
    trip_count: int


@asynccontextmanager
async def lifespan(app):
    db.initialize()
    yield


app = FastAPI(
    title="triplogger", version="1.0.0", lifespan=lifespan,
    description="Log trips, filter origins, and count trips by transport mode. Timestamps use UTC.",
)


@app.exception_handler(psycopg.Error)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Non-finite input values cannot be echoed in JSON.
    errors = [{key: error[key] for key in ("loc", "msg", "type")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.post("/trips", response_model=Trip, status_code=201, tags=["Trips"])
def create_trip(trip: TripInput):
    """Record a completed trip."""
    rows = db.query(
        """INSERT INTO trips (origin_lat, origin_lon, destination_lat, destination_lon,
                              departed_at, transport_mode)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
        (trip.origin_lat, trip.origin_lon, trip.destination_lat, trip.destination_lon,
         trip.departed_at, trip.transport_mode),
    )
    return rows[0]


@app.get("/trips", response_model=list[Trip], tags=["Trips"])
def list_trips(filters: Annotated[ListFilters, Query()]):
    """List matching trips, newest first."""
    where, values = db.build_filters(filters)
    return db.query(
        "SELECT * FROM trips" + where + " ORDER BY departed_at DESC, id DESC LIMIT %s",
        [*values, filters.limit],
    )


@app.get("/stats", response_model=list[ModeCount], tags=["Analytics"])
def statistics(filters: Annotated[Filters, Query()]):
    """Count all matching trips by mode."""
    where, values = db.build_filters(filters)
    return db.query(
        "SELECT transport_mode, COUNT(*) AS trip_count FROM trips" + where
        + " GROUP BY transport_mode ORDER BY transport_mode", values,
    )
