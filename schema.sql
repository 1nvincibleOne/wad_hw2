CREATE TABLE IF NOT EXISTS trips (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    origin_lat DOUBLE PRECISION NOT NULL CHECK (origin_lat BETWEEN -90 AND 90),
    origin_lon DOUBLE PRECISION NOT NULL CHECK (origin_lon BETWEEN -180 AND 180),
    destination_lat DOUBLE PRECISION NOT NULL CHECK (destination_lat BETWEEN -90 AND 90),
    destination_lon DOUBLE PRECISION NOT NULL CHECK (destination_lon BETWEEN -180 AND 180),
    departed_at TIMESTAMPTZ NOT NULL CHECK (isfinite(departed_at)),
    transport_mode TEXT NOT NULL CHECK (transport_mode IN ('walk', 'bicycle', 'car', 'bus'))
);
