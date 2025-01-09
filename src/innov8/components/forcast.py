from datetime import datetime, timezone
from typing import Any

import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, no_update

from innov8.decorators.data_access import callback, data_access


def forecast_button() -> dbc.Button:
    return dbc.Button(
        id="forecast-button",
        children="Forecast",
        outline=True,
        color="success",
        className="row-option flex-center",
    )


# Add forecast ohlc to main chart on button press
@callback(
    Input("forecast-button", "n_clicks"),
    Input("tv-price-chart", "seriesData"),
    State("symbol-dropdown", "value"),
    output={
        "series_data": Output("tv-price-chart", "seriesData", allow_duplicate=True),
        "forecast_button_disabled": Output("forecast-button", "disabled"),
        "forecast_button_clicks": Output("forecast-button", "n_clicks"),
        "forecast_button_color": Output("forecast-button", "color"),
        "forecast_button_style": Output("forecast-button", "style"),
    },
    prevent_initial_call=True,
)
@data_access
def update_price_chart_w_forecast(data, button, series_data, symbol) -> Any:
    output = {
        "series_data": no_update,
        "forecast_button_disabled": False,
        "forecast_button_clicks": no_update,
        "forecast_button_color": "success",
        "forecast_button_style": {},
    }

    # Reset the button
    if ctx.triggered_id != "forecast-button":
        return output | {"forecast_button_clicks": None}

    # Change the button color and style depending on how many times the forecast button has been pressed
    match button:
        case 1:
            color = "warning"
        case 3:
            color = "danger"
        case _:
            color = no_update
    output |= {"forecast_button_color": color}
    match button:
        case 2 | 4:
            output["forecast_button_style"] |= {
                "filter": "hue-rotate(-7deg) contrast(1.05) brightness(0.75)"
            }

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

        return output | {
            "series_data": series_data,
            "forecast_button_disabled": nxt is None,
        }

    return output | {
        "forecast_button_disabled": True,
    }
