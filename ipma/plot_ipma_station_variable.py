#!/usr/bin/env python3
"""Plot all stored observations for one IPMA station and variable with Matplotlib.

Examples:
    python plot_ipma_station_variable_matplotlib.py --list-stations
    python plot_ipma_station_variable_matplotlib.py --list-variables --station 1210881
    python plot_ipma_station_variable_matplotlib.py --station 1210881 --variable temperatura
    python plot_ipma_station_variable_matplotlib.py --station 1210881 --variable temperatura --save temperature.png

Requires Matplotlib: python -m pip install matplotlib
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
except ImportError:
    print(
        "This script needs Matplotlib. Install it with: python -m pip install matplotlib",
        file=sys.stderr,
    )
    raise SystemExit(1)

DEFAULT_DB = "ipma_observations.sqlite3"
VARIABLE_INFO = {
    "temperatura": ("Air temperature", "°C"),
    "humidade": ("Relative humidity", "%"),
    "intensidadeVentoKM": ("Wind speed", "km/h"),
    "intensidadeVento": ("Wind speed", "m/s"),
    "idDireccVento": ("Wind direction", "Direction code"),
    "precAcumulada": ("Hourly precipitation", "mm"),
    "pressao": ("Pressure", "hPa"),
    "radiacao": ("Solar radiation", "kJ/m²"),
}
DIRECTIONS = {0: "Calm", 1: "N", 2: "NE", 3: "E", 4: "SE", 5: "S", 6: "SW", 7: "W", 8: "NW", 9: "N"}


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def list_stations(connection: sqlite3.Connection) -> None:
    try:
        rows = connection.execute("SELECT DISTINCT station FROM obs ORDER BY station").fetchall()
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "Could not read table 'obs'. Run ipma_observations_to_sqlite.py first."
        ) from exc
    if not rows:
        print("No stations found. Populate the database first.")
        return
    for (station,) in rows:
        print(station)


def list_variables(connection: sqlite3.Connection, station: str | None) -> None:
    try:
        if station is None:
            rows = connection.execute(
                "SELECT DISTINCT varname FROM obs ORDER BY varname"
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT DISTINCT varname FROM obs WHERE station = ? ORDER BY varname",
                (station,),
            ).fetchall()
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "Could not read table 'obs'. Run ipma_observations_to_sqlite.py first."
        ) from exc
    if not rows:
        print("No variables found." if station is None else f"No variables found for station {station}.")
        return
    for (variable,) in rows:
        print(variable)


def query_series(
    connection: sqlite3.Connection, station: str, variable: str
) -> tuple[list[datetime], list[float]]:
    try:
        rows = connection.execute(
            """SELECT time, value FROM obs
               WHERE station = ? AND varname = ?
               ORDER BY time""",
            (station, variable),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "Could not read table 'obs'. Run ipma_observations_to_sqlite.py first."
        ) from exc
    if not rows:
        raise RuntimeError(
            f"No data found for station {station!r} and variable {variable!r}. "
            "Use --list-stations and --list-variables to see available values."
        )
    times = [parse_time(timestamp) for timestamp, _ in rows]
    values = [float(value) for _, value in rows]
    return times, values


def plot_series(
    station: str,
    variable: str,
    times: list[datetime],
    values: list[float],
    save: str | None,
) -> None:
    title, unit = VARIABLE_INFO.get(variable, (variable, "Value"))
    is_direction = variable == "idDireccVento"
    color = "#4388c7" if is_direction else "#159a81"

    fig, ax = plt.subplots(figsize=(12, 6.5), constrained_layout=True)
    if is_direction:
        labels = [DIRECTIONS.get(int(value), "Unknown") for value in values]
        ax.step(times, values, where="mid", color=color, linewidth=1.8)
        ax.scatter(times, values, color=color, s=18, zorder=3)
        ax.set_yticks(list(DIRECTIONS), [f"{DIRECTIONS[k]} ({k})" for k in DIRECTIONS])
        ax.set_ylim(-0.5, 9.5)
        ax.set_ylabel("Wind direction")
        # Annotate observed direction names so they remain visible in saved figures.
        for x, y, label in zip(times, values, labels):
            ax.annotate(label, (x, y), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7, alpha=0.8)
    else:
        ax.plot(times, values, color=color, linewidth=1.6)
        if len(times) <= 1500:
            ax.scatter(times, values, color=color, s=10, zorder=3)
        ax.set_ylabel(unit)
        if variable in {"precAcumulada", "radiacao", "intensidadeVentoKM", "intensidadeVento"}:
            ax.set_ylim(bottom=0)
        elif variable == "humidade":
            ax.set_ylim(0, 100)

    ax.set_title(f"{title} · station {station}", loc="left", fontsize=15, fontweight="bold")
    ax.set_xlabel("Time (UTC)")
    ax.grid(True, color="#d9e0e5", linewidth=0.7)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(tz=timezone.utc, maxticks=10))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator(), tz=timezone.utc))
    ax.margins(x=0.01)
    fig.autofmt_xdate()

    if save:
        output = Path(save)
        fig.savefig(output, dpi=160, bbox_inches="tight")
        print(f"Saved plot to {output} ({len(times)} observations)")
        plt.close(fig)
    else:
        print(f"Plotting {len(times)} observations from {times[0]} to {times[-1]} (UTC).")
        plt.show()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB, help=f"SQLite file (default: {DEFAULT_DB})")
    parser.add_argument("--station", help="Station ID as stored in the obs table")
    parser.add_argument("--variable", help="Variable name as stored in the varname column")
    parser.add_argument("--list-stations", action="store_true", help="List station IDs in the database")
    parser.add_argument(
        "--list-variables",
        action="store_true",
        help="List variable names; optionally combine with --station to filter",
    )
    parser.add_argument("--save", metavar="IMAGE", help="Save plot to a file, e.g. PNG or PDF")
    args = parser.parse_args()

    if not (args.list_stations or args.list_variables) and not (args.station and args.variable):
        parser.error("provide --station STATION_ID and --variable VARNAME, or use a listing option")

    try:
        with sqlite3.connect(args.db) as connection:
            if args.list_stations:
                list_stations(connection)
                return 0
            if args.list_variables:
                list_variables(connection, args.station)
                return 0
            times, values = query_series(connection, args.station, args.variable)
        plot_series(args.station, args.variable, times, values, args.save)
    except (OSError, sqlite3.Error, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


