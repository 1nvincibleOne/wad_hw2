import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


def connect():
    return psycopg.connect(
        host=os.environ["DB_HOST"], port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"], connect_timeout=5,
        options="-c timezone=UTC", row_factory=dict_row,
    )


def initialize():
    with connect() as connection:
        connection.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))


def query(sql, values):
    # Commit on success; roll back on failure.
    with connect() as connection:
        return connection.execute(sql, values).fetchall()


def build_filters(filters):
    clauses, values = [], []
    for clause, value in (
        ("transport_mode = %s", filters.mode),
        ("departed_at >= %s", filters.from_time),
        ("departed_at < %s", filters.to_time),
    ):
        if value is not None:
            clauses.append(clause)
            values.append(value)
    if filters.min_lat is not None:
        clauses.append("origin_lat BETWEEN %s AND %s AND origin_lon BETWEEN %s AND %s")
        values.extend([filters.min_lat, filters.max_lat, filters.min_lon, filters.max_lon])
    # Values remain separate from SQL.
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), values
