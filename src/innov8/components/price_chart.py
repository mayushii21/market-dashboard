import os

import dash_bootstrap_components as dbc
import dash_tvlwc
import plotly
from dash import Patch, callback_context
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash_bootstrap_templates import ThemeChangerAIO, template_from_url

from innov8.components.decorators import callback, data_access


def hex_to_rgba(hex_color, alpha=1.0) -> str:
    # Convert hex color to RGBA, handling both three and six character hex codes
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([2 * char for char in hex_color])
    return f"rgba({int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}, {alpha})"


GREEN = "#079A80"
RED = "#F23645"
OPACITY = 0.5


# The price (candlestick) chart
def price_chart() -> dash_tvlwc.Tvlwc:
    return dash_tvlwc.Tvlwc(
        id="tv-price-chart",
        height="calc(100vh - 2em - 83px)",
        width="100%",
    )


# EMA switch with selectable period
def ema_switch() -> dbc.InputGroup:
    return dbc.InputGroup(
        [
            dbc.InputGroupText(
                dbc.Checklist(["EMA"], id="ema", switch=True, persistence=True),
                style={
                    "height": "37px",
                    "display": "flex",
                    "justifyContent": "center",
                    "alignItems": "center",
                    # "borderRadius": "0",
                },
                class_name="btn btn-outline-secondary",
            ),
            dbc.Input(
                id="ema-period",
                placeholder="Period",
                type="number",
                min=1,
                max=200,
                step=1,
                value=9,
                persistence=True,
                style={
                    "paddingLeft": 10,
                    # "borderRadius": "0"
                },
            ),
        ],
    )


# SMA switch with selectable period
def sma_switch() -> dbc.InputGroup:
    return dbc.InputGroup(
        [
            dbc.InputGroupText(
                dbc.Checklist(["SMA"], id="sma", switch=True, persistence=True),
                style={
                    "height": "37px",
                    "display": "flex",
                    "justifyContent": "center",
                    "alignItems": "center",
                    # "borderRadius": "0",
                },
                class_name="btn btn-outline-secondary",
            ),
            dbc.Input(
                id="sma-period",
                placeholder="Period",
                type="number",
                min=1,
                max=200,
                step=1,
                value=50,
                persistence=True,
                style={
                    "paddingLeft": 10,
                    # "borderRadius": "0"
                },
            ),
        ],
    )


# Update price chart (with indicators)
@callback(
    Output("tv-price-chart", "seriesTypes"),
    Output("tv-price-chart", "seriesData"),
    Output("tv-price-chart", "seriesOptions"),
    Output("tv-price-chart", "chartOptions"),
    Input("symbol-dropdown", "value"),
    Input("ema", "value"),
    Input("sma", "value"),
    State("ema-period", "value"),
    State("sma-period", "value"),
    Input(ThemeChangerAIO.ids.radio("theme"), "value"),
    Input("update-state", "data"),
)
@data_access
def update_price_chart(data, symbol, ema, sma, ema_period, sma_period, theme, update):
    # Filter data by ticker symbol and rename for tvlwc
    ticker = data.main_table.loc[
        data.main_table.symbol == symbol,
        ["open", "high", "low", "close", "volume", "date"],
    ].rename(columns={"date": "time", "volume": "value"})

    # Add color for plotting
    ticker["color"] = hex_to_rgba(GREEN, OPACITY)
    ticker["color"] = ticker.color.where(
        ticker["close"] > ticker["open"], hex_to_rgba(RED, OPACITY)
    ).astype("category")
    # Each indicator will have its own color in the chart
    colors = {"SMA": "#1c90d4", "EMA": "#ad0026"}

    # Plot candlesticks (price) and bar chart (volume)
    seriesTypes = ["candlestick", "histogram"]
    seriesData = [
        ticker[["open", "high", "low", "close", "time"]].to_dict("records"),
        ticker[["value", "color", "time"]].to_dict("records"),
    ]
    seriesOptions = [
        {
            "silent-title": "Price",
            "upColor": hex_to_rgba(GREEN, OPACITY),
            "downColor": hex_to_rgba(RED, OPACITY),
            "borderUpColor": GREEN,
            "borderDownColor": RED,
            "wickUpColor": GREEN,
            "wickDownColor": RED,
        },
        {
            "silent-title": "Volume",
            # "color": "#e303fc",
            "priceFormat": {"type": "volume"},
            "priceScaleId": "",
            "scaleMargins": {"top": 0.89, "bottom": 0},
            # "priceLineVisible": False,
        },
    ]

    theme_name = template_from_url(theme)

    template = plotly.io.templates[theme_name]
    text_color = template["layout"]["font"]["color"]
    # bg_color = template["layout"]["plot_bgcolor"]
    grid_color = template["layout"]["scene"]["xaxis"]["gridcolor"]

    def plot_line(indicator) -> None:
        # Plot indicator line
        seriesTypes.append("line")
        seriesData.append(
            ticker[[indicator, "time"]]
            .rename(columns={indicator: "value"})
            .dropna()
            .to_dict("records")
        )
        seriesOptions.append(
            {
                "silent-title": indicator,
                "lineWidth": 3,
                "color": hex_to_rgba(colors[indicator], 0.7),
            }
        )

    # Empty list check
    if ema:
        ticker["EMA"] = (
            ticker["close"]
            .ewm(span=ema_period, min_periods=ema_period, adjust=False)
            .mean()
        )
        plot_line("EMA")
    if sma:
        ticker["SMA"] = ticker["close"].rolling(window=sma_period).mean()
        plot_line("SMA")

    return (
        seriesTypes,
        seriesData,
        seriesOptions,
        {
            "watermark": {
                "visible": True,
                "text": os.getenv("WATERMARK"),
                "color": hex_to_rgba(text_color, 0.3),
                "fontFamily": "Consolas, monospace, Roboto, Ubuntu, sans-serif, 'Trebuchet MS'",
                "fontSize": 72,
            },
            "layout": {
                # "textColor": "#ff80cc",
                "textColor": text_color,
                "background": {"type": "solid", "color": "rgba(0, 0, 0, 0)"},
            },
            "grid": {
                "vertLines": {
                    "color": hex_to_rgba(grid_color, 0.3),
                },
                "horzLines": {
                    "color": hex_to_rgba(grid_color, 0.3),
                },
            },
            "timeScale": {"borderColor": grid_color},
        },
    )


# Update indicators using partial property assignment
@callback(
    Output("tv-price-chart", "seriesData", allow_duplicate=True),
    State("tv-price-chart", "seriesOptions"),
    State("symbol-dropdown", "value"),
    State("ema", "value"),
    State("sma", "value"),
    Input("ema-period", "value"),
    Input("sma-period", "value"),
    prevent_initial_call=True,
)
@data_access
def update_indicator_period(
    data, seriesOptions, symbol, ema, sma, ema_period, sma_period
) -> Patch:
    # Filter data by ticker symbol and rename for tvlwc
    ticker = data.main_table.loc[
        data.main_table.symbol == symbol,
        ["close", "date"],
    ].rename(columns={"date": "time"})

    # If no indicator is selected - prevent update
    if not (ema or sma):
        raise PreventUpdate
    # Store subplot indexes for accessing appropriate data
    tv_indicator_index = {
        seriesOptions[i]["silent-title"]: i for i in range(len(seriesOptions))
    }

    # Creating a Patch object
    patched_seriesData = Patch()
    # Update partial property (y data for indicator)
    if callback_context.triggered_id == "ema-period" and ema:
        ticker["EMA"] = (
            ticker["close"]
            .ewm(span=ema_period, min_periods=ema_period, adjust=False)
            .mean()
        )
        patched_seriesData[tv_indicator_index[ema[0]]] = (
            ticker[["EMA", "time"]]
            .rename(columns={"EMA": "value"})
            .dropna()
            .to_dict("records")
        )
    if callback_context.triggered_id == "sma-period" and sma:
        ticker["SMA"] = ticker["close"].rolling(window=sma_period).mean()
        patched_seriesData[tv_indicator_index[sma[0]]] = (
            ticker[["SMA", "time"]]
            .rename(columns={"SMA": "value"})
            .dropna()
            .to_dict("records")
        )

    return patched_seriesData
