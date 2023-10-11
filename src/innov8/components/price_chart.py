import datetime

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Patch, callback_context, dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash_bootstrap_templates import ThemeChangerAIO, template_from_url
from plotly.subplots import make_subplots

from innov8.components.decorators import callback, data_access


# The price (candlestick) chart
def price_chart():
    return dcc.Graph(id="price-chart")


# EMA switch with selectable period
def ema_switch():
    return dbc.InputGroup(
        [
            dbc.InputGroupText(
                dbc.Checklist(["EMA"], id="ema", switch=True, persistence=True),
                style={
                    "height": "37px",
                    "display": "flex",
                    "justifyContent": "center",
                    "alignItems": "center",
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
                style={"paddingLeft": 10},
            ),
        ],
    )


# SMA switch with selectable period
def sma_switch():
    return dbc.InputGroup(
        [
            dbc.InputGroupText(
                dbc.Checklist(["SMA"], id="sma", switch=True, persistence=True),
                style={
                    "height": "37px",
                    "display": "flex",
                    "justifyContent": "center",
                    "alignItems": "center",
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
                style={"paddingLeft": 10},
            ),
        ],
    )


# Update price chart (with indicators)
@callback(
    Output("price-chart", "figure"),
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
    # Filter data by ticker symbol
    ticker = data.main_table[data.main_table.symbol == symbol].set_index("date")
    green = "#079A80"
    red = "#F23645"
    # Add color for plotting
    ticker["color"] = green
    ticker["color"] = ticker.color.where(ticker["close"] > ticker["open"], red).astype(
        "category"
    )
    # Each indicator will have its own color in the chart
    colors = {"SMA": "#1c90d4", "EMA": "#ad0026"}

    # Create figure with secondary y-axis (for the Volume chart)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Plot candlesticks (price)
    fig.add_trace(
        go.Candlestick(
            x=ticker.index,
            open=ticker.open,
            high=ticker.high,
            low=ticker.low,
            close=ticker.close,
            name="Price",
            increasing_line_color=green,
            decreasing_line_color=red,
        ),
        secondary_y=True,
    )

    # Plot bar chart (volume)
    fig.add_trace(
        go.Bar(
            x=ticker.index,
            y=ticker.volume,
            name="Volume",
            marker_color=ticker.color,
            marker_opacity=0.5,
        ),
        secondary_y=False,
    )

    # Select latest date for specifying default range
    latest_date = ticker.index[-1]
    fig.update_layout(
        template=template_from_url(theme),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, b=7, t=7),
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(
            showgrid=False,
            range=[
                latest_date - datetime.timedelta(180),
                # ticker.index[-1] - relativedelta(months=6),
                latest_date + datetime.timedelta(1),
            ],  # default plot range - 180 days before latest update
            rangeslider=dict(visible=True, bgcolor="rgba(0,0,0,0)"),
            rangebreaks=[
                dict(bounds=["sat", "mon"]),  # hide weekends
                # dict(values=["2015-12-25", "2016-01-01"])  # hide Christmas and New Year's
            ],
            rangeselector=dict(
                bgcolor="rgba(0,0,0,0)",
                buttons=list(
                    [
                        dict(count=1, label="1M", step="month", stepmode="backward"),
                        dict(count=3, label="3M", step="month", stepmode="backward"),
                        dict(count=6, label="6M", step="month", stepmode="backward"),
                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                        dict(count=1, label="1Y", step="year", stepmode="backward"),
                        dict(step="all"),
                    ]
                ),
            ),
            # type="date",
        ),
        yaxis=dict(
            visible=False,
            showgrid=False,
            range=[0, ticker.volume.max() * 4],
            # scaleanchor="y2",
            # scaleratio=0.0000001,
            # constraintoward="bottom",
            rangemode="tozero",
        ),
        yaxis2=dict(
            showgrid=False,
            # tickprefix="$"
        ),
        height=600,
    )

    def plot_line(indicator):
        # Plot indicator
        fig.add_trace(
            go.Scatter(
                x=ticker.index,
                y=ticker[indicator],
                name=indicator,
                mode="lines",
                line={
                    "color": colors[indicator],
                    "width": 3,
                },
                opacity=0.7,
            ),
            secondary_y=True,
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

    return fig


# Update indicators using partial property assignment
@callback(
    Output("price-chart", "figure", allow_duplicate=True),
    State("price-chart", "figure"),
    State("symbol-dropdown", "value"),
    State("ema", "value"),
    State("sma", "value"),
    Input("ema-period", "value"),
    Input("sma-period", "value"),
    prevent_initial_call=True,
)
@data_access
def update_indicator_period(data, fig, symbol, ema, sma, ema_period, sma_period):
    # Filter data by ticker symbol
    ticker = data.main_table[data.main_table.symbol == symbol].set_index("date")
    # If no indicator is selected - prevent update
    if not (ema or sma):
        raise PreventUpdate
    # Store subplot indexes for accessing appropriate data
    fig_index = {fig["data"][i]["name"]: i for i in range(len(fig["data"]))}
    # Creating a Patch object
    patched_figure = Patch()
    # Update partial property (y data for indicator)
    if callback_context.triggered_id == "ema-period" and ema:
        patched_figure.data[fig_index[ema[0]]].y = (
            ticker["close"]
            .ewm(span=ema_period, min_periods=ema_period, adjust=False)
            .mean()
        )
    if callback_context.triggered_id == "sma-period" and sma:
        patched_figure.data[fig_index[sma[0]]].y = (
            ticker["close"].rolling(window=sma_period).mean()
        )

    return patched_figure
