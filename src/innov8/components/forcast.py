from datetime import datetime, timedelta, timezone
from typing import Any

import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, no_update
from loguru import logger

from innov8.components.decorators import callback, data_access


def forecast_button() -> dbc.Button:
    return dbc.Button(
        id="forecast-button",
        children="Forecast",
        outline=True,
        color="info",
        style={
            "height": "37px",
            "width": "37px",
            "minWidth": "fit-content",
            "display": "flex",
            "justifyContent": "center",
            "alignItems": "center",
        },
    )


# Add forecast ohlc to main chart on button press
@callback(
    Output("tv-price-chart", "seriesData", allow_duplicate=True),
    Output("forecast-button", "disabled"),
    Input("forecast-button", "n_clicks"),
    State("tv-price-chart", "seriesData"),
    Input("symbol-dropdown", "value"),
    prevent_initial_call=True,
)
@data_access
def update_price_chart_w_forcast(data, button, series_data, symbol) -> Any:
    if ctx.triggered_id != "forecast-button":
        return no_update, False

    date = series_data[0][-1]["time"]

    date_obj = datetime(
        day=date["day"], month=date["month"], year=date["year"], tzinfo=timezone.utc
    )
    date_obj = date_obj + timedelta(days=1)

    forecast = data.get_forecasts(symbol, date_obj.timestamp())

    if forecast:
        series_data[0].append(
            {
                "open": forecast[0],
                "high": forecast[1],
                "low": forecast[2],
                "close": forecast[3],
                "time": datetime.fromtimestamp(forecast[4], tz=timezone.utc),
            }
        )

        nxt = data.get_forecasts(symbol, (date_obj + timedelta(days=1)).timestamp())

        return series_data, nxt is None
