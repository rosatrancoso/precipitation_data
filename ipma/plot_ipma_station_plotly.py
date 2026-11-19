#!/usr/bin/env python3
"""Interactive Plotly meteogram for one station in the IPMA SQLite database.

Examples:
    python plot_ipma_station_plotly.py --list-stations
    python plot_ipma_station_plotly.py --station 1210881
    python plot_ipma_station_plotly.py --db ipma.sqlite3 --station 1210881 --save olhao.html

Requires Plotly: python -m pip install plotly
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    print(
        "This script needs Plotly. Install it with: python -m pip install plotly",
        file=sys.stderr,
    )
    raise SystemExit(1)

DEFAULT_DB = "ipma_observations.sqlite3"
DIRECTIONS = {
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
    try:
        rows = connection.execute(
            "SELECT DISTINCT station FROM obs ORDER BY station"
        ).fetchall()
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "Could not read table 'obs'. Run ipma_observations_to_sqlite.py first."
        ) from exc
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
    window = {t: values for t, values in observations.items() if start <= t <= end}
    return window, start, end


def make_figure(
    station: str,
    observations: dict[datetime, dict[str, float]],
    start: datetime,
    end: datetime,
) -> go.Figure:
    times = sorted(observations)
    figure = make_subplots(
        rows=4,
        cols=2,
        shared_xaxes=True,
        vertical_spacing=0.09,
        horizontal_spacing=0.11,
        subplot_titles=(
            "Temperature",
            "Relative humidity",
            "Wind speed",
            "Wind direction",
            "Accumulated precipitation",
            "Hourly precipitation",
            "Pressure",
            "Radiation",
        ),
    )

    colors = {
        "temperature": "#159a81",
        "humidity": "#8064b8",
        "wind": "#dc8b2f",
        "direction": "#4388c7",
        "accumulated": "#258ba5",
        "hourly": "#4a82c1",
        "pressure": "#cb6479",
        "radiation": "#bd9c25",
    }

    def values_for(variable: str) -> list[float | None]:
        return [observations[t].get(variable) for t in times]

    def add_line(row: int, col: int, variable: str, name: str, unit: str, color: str) -> None:
        values = values_for(variable)
        figure.add_trace(
            go.Scatter(
                x=times,
                y=values,
                mode="lines+markers",
                name=name,
                line={"color": color, "width": 2},
                marker={"size": 5},
                connectgaps=False,
                customdata=[[unit] for _ in values],
                hovertemplate="%{x|%d %b %H:%M} UTC<br>%{y:.2f} %{customdata[0]}<extra></extra>",
                showlegend=False,
            ),
            row=row,
            col=col,
        )

    add_line(1, 1, "temperatura", "Temperature", "°C", colors["temperature"])
    figure.update_yaxes(title_text="°C", row=1, col=1)

    add_line(1, 2, "humidade", "Relative humidity", "%", colors["humidity"])
    figure.update_yaxes(title_text="%", range=[0, 100], row=1, col=2)

    add_line(2, 1, "intensidadeVentoKM", "Wind speed", "km/h", colors["wind"])
    figure.update_yaxes(title_text="km/h", rangemode="tozero", row=2, col=1)

    direction_values = values_for("idDireccVento")
    direction_text = [
        DIRECTIONS.get(int(value), "Unknown") if value is not None else "No data"
        for value in direction_values
    ]
    figure.add_trace(
        go.Scatter(
            x=times,
            y=direction_values,
            mode="lines+markers",
            name="Wind direction",
            line={"color": colors["direction"], "width": 2, "shape": "hv"},
            marker={"size": 6},
            connectgaps=False,
            customdata=direction_text,
            hovertemplate="%{x|%d %b %H:%M} UTC<br>%{customdata} (idDireccVento=%{y})<extra></extra>",
            showlegend=False,
        ),
        row=2,
        col=2,
    )
    figure.update_yaxes(
        title_text="Direction",
        tickmode="array",
        tickvals=list(DIRECTIONS),
        ticktext=[f"{DIRECTIONS[k]} ({k})" for k in DIRECTIONS],
        range=[-0.5, 9.5],
        row=2,
        col=2,
    )

    hourly_rain = values_for("precAcumulada")
    accumulated_rain: list[float | None] = []
    running_total = 0.0
    for value in hourly_rain:
        if value is None:
            accumulated_rain.append(None)
        else:
            running_total += value
            accumulated_rain.append(running_total)
    figure.add_trace(
        go.Scatter(
            x=times,
            y=accumulated_rain,
            mode="lines+markers",
            name="Accumulated precipitation",
            line={"color": colors["accumulated"], "width": 2},
            marker={"size": 5},
            connectgaps=False,
            hovertemplate="%{x|%d %b %H:%M} UTC<br>%{y:.2f} mm<extra></extra>",
            showlegend=False,
        ),
        row=3,
        col=1,
    )
    figure.update_yaxes(title_text="mm · running 24h sum", rangemode="tozero", row=3, col=1)

    figure.add_trace(
        go.Bar(
            x=times,
            y=hourly_rain,
            name="Hourly precipitation",
            marker_color=colors["hourly"],
            opacity=0.85,
            hovertemplate="%{x|%d %b %H:%M} UTC<br>%{y:.2f} mm in hour<extra></extra>",
            showlegend=False,
        ),
        row=3,
        col=2,
    )
    figure.update_yaxes(title_text="mm per hour", rangemode="tozero", row=3, col=2)

    add_line(4, 1, "pressao", "Pressure", "hPa", colors["pressure"])
    figure.update_yaxes(title_text="hPa", row=4, col=1)

    add_line(4, 2, "radiacao", "Radiation", "kJ/m²", colors["radiation"])
    figure.update_yaxes(title_text="kJ/m²", rangemode="tozero", row=4, col=2)

    figure.update_xaxes(range=[start, end], tickformat="%H:%M", showgrid=True, gridcolor="#e1e6ea")
    figure.update_yaxes(showgrid=True, gridcolor="#e1e6ea", zerolinecolor="#cbd3d8")
    figure.update_layout(
        title={"text": f"IPMA station {station} · latest 24 hours (UTC)", "x": 0.02},
        template="plotly_white",
        height=1050,
        hovermode="x unified",
        bargap=0.18,
        margin={"l": 70, "r": 28, "t": 90, "b": 50},
        font={"family": "Arial, sans-serif", "size": 12},
    )
    figure.update_xaxes(title_text="Time (UTC)", row=4, col=1)
    figure.update_xaxes(title_text="Time (UTC)", row=4, col=2)
    return figure


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB, help=f"SQLite file (default: {DEFAULT_DB})")
    parser.add_argument("--station", help="IPMA station ID stored in the obs table")
    parser.add_argument("--list-stations", action="store_true", help="List station IDs present in the database")
    parser.add_argument("--save", metavar="HTML", help="Save an interactive standalone HTML plot")
    args = parser.parse_args()

    if not args.list_stations and not args.station:
        parser.error("provide --station STATION_ID or use --list-stations")

    try:
        with sqlite3.connect(args.db) as connection:
            if args.list_stations:
                list_stations(connection)
                return 0
            observations, start, end = load_station_data(connection, args.station)
        figure = make_figure(args.station, observations, start, end)
        if args.save:
            output = Path(args.save)
            figure.write_html(output, include_plotlyjs=True, full_html=True)
            print(f"Saved interactive plot to {output}")
        else:
            figure.show()
    except (OSError, sqlite3.Error, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
