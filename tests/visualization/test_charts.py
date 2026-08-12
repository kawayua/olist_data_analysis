import pandas as pd

from src.visualization.charts import line_chart


def test_line_chart_uses_requested_columns():
    frame = pd.DataFrame({"month": ["2024-01"], "revenue": [100.0]})

    figure = line_chart(frame, x="month", y="revenue", title="Revenue")

    assert figure.data[0].x[0] == "2024-01"
    assert figure.data[0].y[0] == 100.0
