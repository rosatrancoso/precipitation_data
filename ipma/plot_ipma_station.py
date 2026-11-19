#!/usr/bin/env python3
"""Plot the latest 24 hours of IPMA observations for one station from SQLite.

Examples:
    python plot_ipma_station.py --list-stations
    python plot_ipma_station.py --station 1210881
    python plot_ipma_station.py --db ipma.sqlite3 --station 1210881 --save olhao.png

Requires matplotlib: python -m pip install matplotlib
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
except ImportError:
    print(
        "This script needs matplotlib. Install it with: python -m pip install matplotlib",
        file=sys.stderr,
    )
    raise SystemExit(1)

DEFAULT_DB = "ipma_observations.sqlite3"
DIRECTION_LABELS = {
    0: "Calm",
    1: "N",
    2: "NE",
    3: "E",
    4: "SE",
    5: "S",
    6: "SW",
    7: "W",
    8: "NW",
    9: "N",
}


def parse_time(value: str) -> datetime:
    """Parse IPMA/ISO timestamps and normalize them to UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def list_stations(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        "SELECT DISTINCT station FROM obs ORDER BY station"
    ).fetchall()
    if not rows:
        print("No stations found. Populate the database first.")
        return
    print("Stations in database:")
    for (station,) in rows:
        print(station)


def load_station_data(
    connection: sqlite3.Connection, station: str
) -> tuple[dict[datetime, dict[str, float]], datetime, datetime]:
    try:
        records = connection.execute(
            "SELECT time, varname, value FROM obs WHERE station = ? ORDER BY time",
            (station,),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "Could not read table 'obs'. Run ipma_observations_to_sqlite.py first."
        ) from exc

    if not records:
        raise RuntimeError(f"No observations found for station {station!r}.")

    observations: dict[datetime, dict[str, float]] = {}
    for timestamp, varname, value in records:
        when = parse_time(timestamp)
        observations.setdefault(when, {})[varname] = float(value)

    end = max(observations)
    start = end - timedelta(hours=24)
    window = {t: v for t, v in observations.items() if start <= t <= end}
    return window, start, end


def plot_station(station: str, observations: dict[datetime, dict[str, float]], start: datetime, end: datetime, save: str | None) -> None:
    timestamps = sorted(observations)
    fig, axes = plt.subplots(
        4, 2, figsize=(13, 10), sharex=True, constrained_layout=True
    )
    fig.suptitle(f"IPMA station {station} · latest 24 hours", fontsize=16, fontweight="bold")

    plot_specs = [
        ("temperatura", "Temperature", "°C", "#159a81"),
        ("humidade", "Relative humidity", "%", "#8064b8"),
        ("intensidadeVentoKM", "Wind speed", "km/h", "#dc8b2f"),
        ("idDireccVento", "Wind direction", "Direction", "#4388c7"),
        ("__precip_cumulative__", "Accumulated precipitation", "mm · running 24-hour sum", "#258ba5"),
        ("precAcumulada", "Hourly precipitation", "mm per hour", "#4a82c1"),
        ("pressao", "Pressure", "hPa", "#cb6479"),
        ("radiacao", "Radiation", "kJ/m²", "#bd9c25"),
    ]

    hourly_rain: list[tuple[datetime, float]] = []
    for when in timestamps:
        value = observations[when].get("precAcumulada")
        if value is not None:
            hourly_rain.append((when, value))
    cumulative: list[tuple[datetime, float]] = []
    running_total = 0.0
    for when, value in hourly_rain:
        running_total += value
        cumulative.append((when, running_total))

    for ax, (variable, title, unit, color) in zip(axes.flat, plot_specs):
        ax.set_title(title, loc="left", fontsize=11, fontweight="semibold")
        ax.set_ylabel(unit, fontsize=9)
        ax.grid(True, color="#d9e0e5", linewidth=0.7, alpha=0.8)
        ax.set_xlim(start, end)
        ax.margins(x=0)

        if variable == "__precip_cumulative__":
            points = cumulative
            if points:
                times, values = zip(*points)
                ax.plot(times, values, color=color, linewidth=1.8, marker="o", markersize=2.5)
                ax.fill_between(times, values, color=color, alpha=0.12)
            else:
                ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", color="#73808a")
        elif variable == "precAcumulada":
            points = hourly_rain
            if points:
                times, values = zip(*points)
                ax.bar(times, values, width=timedelta(minutes=42), color=color, alpha=0.85, align="center")
            else:
                ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", color="#73808a")
        elif variable == "idDireccVento":
            points = [
                (when, values[variable])
                for when, values in observations.items()
                if variable in values and int(values[variable]) in DIRECTION_LABELS
            ]
            if points:
                times, values = zip(*points)
                ax.step(times, values, where="mid", color=color, linewidth=1.8)
                ax.scatter(times, values, color=color, s=16, zorder=3)
                ax.set_yticks(range(10), [f"{DIRECTION_LABELS[i]} ({i})" for i in range(10)], fontsize=8)
                ax.set_ylim(-0.5, 9.5)
            else:
                ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", color="#73808a")
        else:
            points = [
                (when, values[variable])
                for when, values in observations.items()
                if variable in values
            ]
            if points:
                times, values = zip(*points)
                ax.plot(times, values, color=color, linewidth=1.8, marker="o", markersize=2.5)
            else:
                ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", color="#73808a")

    locator = mdates.HourLocator(interval=4, tz=timezone.utc)
    formatter = mdates.DateFormatter("%d-%b-%Y\n%H:%M", tz=timezone.utc)
    for ax in axes[-1, :]:
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        ax.set_xlabel("Time (UTC)", fontsize=9)
    for ax in axes.flat:
        ax.tick_params(axis="x", labelsize=8)
        ax.tick_params(axis="y", labelsize=8)

    if save:
        output = Path(save)
        fig.savefig(output, dpi=160, bbox_inches="tight")
        print(f"Saved plot to {output}")
    else:
        plt.show()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB, help=f"SQLite file (default: {DEFAULT_DB})")
    parser.add_argument("--station", help="IPMA station ID stored in the obs table")
    parser.add_argument("--list-stations", action="store_true", help="List station IDs present in the database")
    parser.add_argument("--save", metavar="PNG", help="Save the plot to a file instead of opening a window")
    args = parser.parse_args()

    if not args.list_stations and not args.station:
        parser.error("provide --station STATION_ID or use --list-stations")

    try:
        with sqlite3.connect(args.db) as connection:
            if args.list_stations:
                list_stations(connection)
                return 0
            observations, start, end = load_station_data(connection, args.station)
        plot_station(args.station, observations, start, end, args.save)
    except (OSError, sqlite3.Error, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
