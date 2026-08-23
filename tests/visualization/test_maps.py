import pandas as pd

from src.visualization.maps import brazil_state_polygon_map

GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"sigla": "SP"},
            "geometry": {"type": "Polygon", "coordinates": []},
        }
    ],
}


def test_brazil_state_polygon_map_draws_geojson_polygons_with_payment_tooltips():
    frame = pd.DataFrame(
        {
            "customer_state": ["SP"],
            "payment_value": [150.5],
            "customer_count": [12],
        }
    )

    figure = brazil_state_polygon_map(
        frame,
        geojson=GEOJSON,
        color_metric="payment_value",
        hover_metrics=("payment_value", "customer_count"),
        title="客户支付金额与人数分布",
    )

    state_trace = figure.data[0]

    assert state_trace.fill == "toself"
    assert state_trace.hoveron == "fills"
    assert state_trace.hoverinfo == "text"
    assert "支付金额" in state_trace.text
    assert "客户数" in state_trace.text
    assert state_trace.name == state_trace.text
    assert figure.data[-1].marker.showscale is True
    assert figure.data[-1].marker.colorbar.title.text == "支付金额"


def test_brazil_state_polygon_map_uses_review_score_in_hover_details():
    frame = pd.DataFrame(
        {
            "customer_state": ["SP"],
            "item_revenue": [250.0],
            "customer_count": [8],
            "average_review_score": [4.25],
        }
    )

    figure = brazil_state_polygon_map(
        frame,
        geojson=GEOJSON,
        color_metric="item_revenue",
        hover_metrics=("item_revenue", "customer_count", "average_review_score"),
        title="商品销售额、人数与平均评分",
    )

    assert figure.data[-1].marker.colorbar.title.text == "商品销售额"
    assert figure.data[0].hoverinfo == "text"
    assert "平均评分" in figure.data[0].text
