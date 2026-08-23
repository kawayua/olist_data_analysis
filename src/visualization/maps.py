"""Interactive geographic chart factories for Brazilian state performance."""

from __future__ import annotations

import gzip
import json
from typing import Any
from urllib.request import urlopen

import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale

from app.components.presentation import display_label

BRAZIL_STATES_GEOJSON_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
    "?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF"
)

IBGE_STATE_CODES = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
    "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
    "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
    "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
    "52": "GO", "53": "DF",
}

MAP_METRIC_LABELS = {
    "payment_value": "支付金额",
    "item_revenue": "商品销售额",
}


def load_brazil_states_geojson() -> dict[str, Any]:
    """Return the official IBGE GeoJSON boundary collection for Brazilian states."""
    with urlopen(BRAZIL_STATES_GEOJSON_URL, timeout=15) as response:  # nosec B310
        payload = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            payload = gzip.decompress(payload)
    geojson = json.loads(payload)
    for feature in geojson["features"]:
        state_code = feature["properties"].get("codarea")
        feature["properties"]["sigla"] = IBGE_STATE_CODES.get(state_code, state_code)
    return geojson


def _metric_label(metric: str) -> str:
    return MAP_METRIC_LABELS.get(metric, display_label(metric))


def _format_hover_value(metric: str, value: float) -> str:
    if metric in {"payment_value", "item_revenue"}:
        return f"R${value:,.2f}"
    if metric == "average_review_score":
        return f"{value:.3f}分"
    return f"{value:,.0f}"


def _geometry_rings(feature: dict[str, Any]) -> list[list[list[float]]]:
    """Return the polygon rings for either GeoJSON polygon geometry type."""
    geometry = feature["geometry"]
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    if geometry["type"] == "MultiPolygon":
        return [ring for polygon in geometry["coordinates"] for ring in polygon]
    raise ValueError(f"不支持的州界几何类型：{geometry['type']}")


def brazil_state_polygon_map(
    frame: pd.DataFrame,
    *,
    geojson: dict[str, Any],
    color_metric: str,
    hover_metrics: tuple[str, ...],
    title: str,
) -> go.Figure:
    """Render Brazilian state polygons on standard Plotly Cartesian axes."""
    required_columns = {"customer_state", color_metric, *hover_metrics}
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        raise ValueError(f"州地图缺少字段：{sorted(missing_columns)}")

    metrics_by_state = frame.set_index("customer_state")
    color_values = frame[color_metric].astype(float)
    color_min, color_max = color_values.min(), color_values.max()
    color_span = color_max - color_min
    figure = go.Figure()

    for feature in geojson["features"]:
        state_code = feature["properties"]["sigla"]
        if state_code not in metrics_by_state.index:
            continue
        row = metrics_by_state.loc[state_code]
        normalized = 0.5 if color_span == 0 else (row[color_metric] - color_min) / color_span
        fill_color = sample_colorscale("Blues", float(normalized))[0]
        x_values: list[float | None] = []
        y_values: list[float | None] = []
        for ring in _geometry_rings(feature):
            x_values.extend(point[0] for point in ring)
            y_values.extend(point[1] for point in ring)
            x_values.append(None)
            y_values.append(None)
        hover_lines = [f"客户所在州：{state_code}"]
        hover_lines.extend(
            f"{_metric_label(metric)}：{_format_hover_value(metric, row[metric])}"
            for metric in hover_metrics
        )
        hover_text = "<br>".join(hover_lines)
        figure.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode="lines",
                fill="toself",
                fillcolor=fill_color,
                line={"color": "#FFFFFF", "width": 1.2},
                hoveron="fills",
                # Filled polygons use the trace text for hover events.  A
                # hovertemplate alone is ignored by some Plotly renderers,
                # which then falls back to the default "trace N" label.
                text=hover_text,
                name=hover_text,
                hoverinfo="text",
                showlegend=False,
            )
        )

    figure.add_trace(
        go.Scatter(
            x=[None, None],
            y=[None, None],
            mode="markers",
            marker={
                "size": 0.1,
                "color": [color_min, color_max],
                "colorscale": "Blues",
                "showscale": True,
                "colorbar": {"title": _metric_label(color_metric), "len": 0.7},
            },
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.update_layout(
        title={"text": title, "font": {"size": 16, "color": "#13233D"}},
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 0, "r": 0, "t": 45, "b": 0},
        hoverlabel={"bgcolor": "#172B4D", "font": {"color": "#FFFFFF"}},
    )
    figure.update_xaxes(visible=False, showgrid=False, zeroline=False)
    figure.update_yaxes(
        visible=False,
        showgrid=False,
        zeroline=False,
        scaleanchor="x",
        scaleratio=1,
    )
    return figure
