from typing import Any

from dash import html
from dash.dependencies import Input, Output

from innov8.decorators.data_access import callback


def initial_load() -> html.Div:
    """Initial loading spinner indicator"""
    return html.Div(id="initial-load", className="_dash-loading visible")


@callback(
    Output("initial-load", "className"),
    Input("52-week-price-chart", "figure"),
    Input("52-week-high-low-indicator", "figure"),
)
def disable_spinner(*args: Any, **kwargs: Any) -> Any:
    """Disable spinner when the last loaded charts are ready and enable main chart visibility"""
    return ""
