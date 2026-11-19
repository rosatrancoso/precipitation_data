#!/usr/bin/env python3
"""Plot every stored observation for one IPMA station and variable.

Examples:
    python plot_ipma_station_variable.py --list-stations
    python plot_ipma_station_variable.py --list-variables --station 1210881
    python plot_ipma_station_variable.py --station 1210881 --variable temperatura
    python plot_ipma_station_variable.py --station 1210881 --variable temperatura --save temperature.html

Requires Plotly: python -m pip install plotly
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import plotly.graph_objects as go
except ImportError:
    print(
        "This script needs Plotly. Install it with: python -m pip install plotly",
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
    rows = connection.execute("SELECT DISTINCT station FROM obs ORDER BY station").fetchall()
    if not rows:
        print("No stations found. Populate the database first.")
        return
    for (station,) in rows:
        print(station)


def list_variables(connection: sqlite3.Connection, station: str | None) -> None:
    if station is None:
        rows = connection.execute(
            "SELECT DISTINCT varname FROM obs ORDER BY varname"
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT DISTINCT varname FROM obs WHERE station = ? ORDER BY varname",
            (station,),
        ).fetchall()
    if not rows:
        print("No variables found." if station is None else f"No variables found for station {station}.")
        return
    for (variable,) in rows:
        print(variable)


def query_series(
    connection: sqlite3.Connection, station: str, variable: str
) -> tuple[list[datetime], list[float]]:
    rows = connection.execute(
        """SELECT time, value FROM obs
           WHERE station = ? AND varname = ?
           ORDER BY time""",
        (station, variable),
    ).fetchall()
    if not rows:
        raise RuntimeError(
            f"No data found for station {station!r} and variable {variable!r}. "
            "Use --list-stations and --list-variables to see available values."
        )
    times = [parse_time(timestamp) for timestamp, _ in rows]
    values = [float(value) for _, value in rows]
    return times, values


def plot_series(station: str, variable: str, times: list[datetime], values: list[float]) -> go.Figure:
    title, unit = VARIABLE_INFO.get(variable, (variable, "Value"))
    is_direction = variable == "idDireccVento"
    color = "#4388c7" if is_direction else "#159a81"
    direction_names = [DIRECTIONS.get(int(value), "Unknown") for value in values] if is_direction else None
    mode = "lines+markers" if len(times) <= 2000 else "lines"

    trace = go.Scatter(
        x=times,
        y=values,
        mode=mode,
        name=title,
        line={"color": color, "width": 2, "shape": "hv" if is_direction else "linear"},
        marker={"size": 5},
        customdata=direction_names,
        hovertemplate=(
            "%{x|%d %b %Y %H:%M} UTC<br>%{customdata} (code %{y})<extra></extra>"
            if is_direction
            else f"%{{x|%d %b %Y %H:%M}} UTC<br>%{{y:.3f}} {unit}<extra></extra>"
        ),
    )
    figure = go.Figure(trace)
    figure.update_layout(
        title={"text": f"{title} · station {station}", "x": 0.02},
        template="plotly_white",
        height=620,
        hovermode="x unified",
        margin={"l": 75, "r": 30, "t": 80, "b": 65},
        xaxis_title="Time (UTC)",
        yaxis_title=unit,
        showlegend=False,
    )
    figure.update_xaxes(showgrid=True, gridcolor="#e1e6ea", rangeslider_visible=True)
    figure.update_yaxes(showgrid=True, gridcolor="#e1e6ea", zerolinecolor="#cbd3d8")
    if is_direction:
        figure.update_yaxes(
            tickmode="array",
            tickvals=list(DIRECTIONS),
            ticktext=[f"{DIRECTIONS[k]} ({k})" for k in DIRECTIONS],
            range=[-0.5, 9.5],
        )
    elif variable == "humidade":
        figure.update_yaxes(range=[0, 100])
    elif variable in {"precAcumulada", "radiacao", "intensidadeVentoKM", "intensidadeVento"}:
        figure.update_yaxes(rangemode="tozero")
    return figure


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
    parser.add_argument("--save", metavar="HTML", help="Save interactive plot as standalone HTML")
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
        figure = plot_series(args.station, args.variable, times, values)
        if args.save:
            output = Path(args.save)
            figure.write_html(output, include_plotlyjs=True, full_html=True)
            print(f"Saved interactive plot to {output} ({len(times)} observations)")
        else:
            print(f"Plotting {len(times)} observations from {times[0]} to {times[-1]} (UTC).")
            figure.show()
    except (OSError, sqlite3.Error, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
