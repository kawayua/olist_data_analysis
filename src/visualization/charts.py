"""Pure Plotly chart factories used by Streamlit pages."""

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure


def line_chart(frame: pd.DataFrame, x: str, y: str, title: str) -> Figure:
    """Return a line chart using the requested DataFrame columns."""
    return px.line(frame, x=x, y=y, title=title)
