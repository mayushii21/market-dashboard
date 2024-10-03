from datetime import datetime, timezone
from typing import Any

import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, no_update

from innov8.components.decorators import callback, data_access


def forecast_button() -> dbc.Button:
    return dbc.Button(
        id="forecast-button",
        children="Forecast",
        outline=True,
        color="success",
        style={"height": "37px", "width": "100%"},
    )


# Add forecast ohlc to main chart on button press
@callback(
    Output("tv-price-chart", "seriesData", allow_duplicate=True),
    Output("forecast-button", "disabled"),
    Output("forecast-button", "n_clicks"),
    Output("forecast-button", "color"),
    Output("forecast-button", "style"),
    Input("forecast-button", "n_clicks"),
    State("tv-price-chart", "seriesData"),
    Input("symbol-dropdown", "value"),
    Input("update-state", "data"),
    prevent_initial_call=True,
)
@data_access
def update_price_chart_w_forecast(data, button, series_data, symbol, _) -> Any:
    style = {"height": "37px", "width": "100%"}

    # On initial render or ticker switch
    if ctx.triggered_id != "forecast-button" or ctx.triggered_id == "update-state":
        return (no_update, False, None, "success", style)

    # Change the button color and style depending on how many times the forecast button has been pressed
    match button:
        case 1:
            color = "warning"
        case 3:
            color = "danger"
        case _:
            color = no_update
    match button:
        case 2 | 4:
            style |= {"filter": "hue-rotate(-7deg) contrast(1.05) brightness(0.75)"}

    date = series_data[0][-1]["time"]

    date_obj = datetime(
        day=date["day"], month=date["month"], year=date["year"], tzinfo=timezone.utc
    )

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

        nxt = data.get_forecasts(symbol, forecast[4])

        return series_data, nxt is None, no_update, color, style

    return (no_update, True, no_update, color, style)
