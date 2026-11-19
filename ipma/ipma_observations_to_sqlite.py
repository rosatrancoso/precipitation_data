#!/usr/bin/env python3
"""Download IPMA hourly station observations into a SQLite `obs` table.

Usage:
    python ipma_observations_to_sqlite.py --db ipma.sqlite3

Rows are keyed by (time, station, varname). Re-running the script updates
existing values and inserts new observations. IPMA's -99.0 nodata sentinel
is omitted.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

OBSERVATIONS_URL = (
    "https://api.ipma.pt/open-data/observation/meteorology/stations/"
    "observations.json"
)


def fetch_observations(url: str, timeout: float) -> dict[str, Any]:
    request = Request(
        url,
        headers={"User-Agent": "ipma-observations-sqlite/1.0"},
    )
    with urlopen(request, timeout=timeout) as response:
        payload = response.read()
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Expected the API response to be a JSON object.")
    return data


def observation_rows(data: dict[str, Any]) -> tuple[list[tuple[str, str, str, float]], int]:
    """Flatten timestamp -> station -> variable readings into database rows."""
    rows: list[tuple[str, str, str, float]] = []
    skipped_nodata = 0

    for timestamp, stations in data.items():
        if not isinstance(stations, dict):
            continue
        for station_id, variables in stations.items():
            if not isinstance(variables, dict):
                continue
            for variable, raw_value in variables.items():
                if raw_value is None or isinstance(raw_value, bool):
                    continue
                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(value):
                    continue
                if value == -99.0:
                    skipped_nodata += 1
                    continue
                rows.append((str(timestamp), str(station_id), str(variable), value))

    return rows, skipped_nodata


def update_database(db_path: str, rows: list[tuple[str, str, str, float]]) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS obs (
                   time TEXT NOT NULL,
                   station TEXT NOT NULL,
                   varname TEXT NOT NULL,
                   value REAL NOT NULL
               )"""
        )
        connection.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS obs_time_station_varname_uq
               ON obs (time, station, varname)"""
        )
        connection.executemany(
            """INSERT INTO obs (time, station, varname, value)
               VALUES (?, ?, ?, ?)
               ON CONFLICT (time, station, varname)
               DO UPDATE SET value = excluded.value""",
            rows,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        default="ipma_observations.sqlite3",
        help="SQLite database file (default: %(default)s)",
    )
    parser.add_argument(
        "--url",
        default=OBSERVATIONS_URL,
        help="IPMA observations JSON URL (default: official hourly endpoint)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds (default: %(default)s)",
    )
    args = parser.parse_args()

    try:
        data = fetch_observations(args.url, args.timeout)
        rows, skipped_nodata = observation_rows(data)
        update_database(args.db, rows)
    except (URLError, TimeoutError, OSError, ValueError, sqlite3.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Updated {len(rows)} observation rows in {args.db}; "
        f"skipped {skipped_nodata} nodata values."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
