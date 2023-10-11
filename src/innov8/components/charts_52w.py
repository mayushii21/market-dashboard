import dash_trich_components as dtc
import plotly.graph_objects as go
from dash import dcc
from dash.dependencies import Input, Output
from dash_bootstrap_templates import ThemeChangerAIO, template_from_url

from innov8.components.decorators import callback, data_access


# Carousel showing 52-week data
def carousel_52_week():
    return dtc.Carousel(
        [
            dcc.Graph(id="52-week-price-chart"),
            dcc.Graph(id="52-week-high-low-indicator"),
        ],
        slides_to_show=1,
        vertical=True,
        autoplay=True,
        speed=3000,
        style={
            "height": 280,
            "width": 357,
        },
        responsive=[
            {"breakpoint": 9999, "settings": {"arrows": False}},
        ],
    )


# This function is responsible for updating the weekly price chart and the gauge (speedometer) chart
@callback(
    Output("52-week-price-chart", "figure"),
    Output("52-week-high-low-indicator", "figure"),
    Input("symbol-dropdown", "value"),
    Input(ThemeChangerAIO.ids.radio("theme"), "value"),
    Input("update-state", "data"),
)
@data_access
def update_52_week_charts(data, symbol, theme, update):
    # Filter data by ticker symbol
    ticker = data.main_table[data.main_table.symbol == symbol].set_index("date")

    # The output from this resample operation feeds the weekly closing price chart
    weekly_52 = (
        ticker.resample(
            "W-MON",
            closed="left",
            label="left",
        )["close"]
        .last()
        .iloc[-52:]
    )

    # Plot 52 week chart (price)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=weekly_52.index,
            y=weekly_52.values,
            line_width=3,
        )
    )
    fig.update_layout(
        template=template_from_url(theme),  # set theme
        title={"text": "Weekly Chart", "y": 0.9},
        font_size=9,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=280,
        width=357,
        margin=dict(l=1, r=1, b=0, t=0),
        showlegend=False,
    )
    fig.update_xaxes(showticklabels=False, showgrid=False)
    fig.update_yaxes(showticklabels=False, showgrid=False)

    # Get 52-week low/high and current price
    df_52_week_low = ticker.close[-252:].min()
    df_52_week_high = ticker.close[-252:].max()
    current_price = ticker.iat[-1, ticker.columns.get_loc("close")]

    # Plot gauge (speedometer) chart which indicates the tickers current price compared to it's 52-week high/low
    fig2 = go.Figure()
    fig2.add_trace(
        go.Indicator(
            value=current_price,
            mode="gauge",
            gauge={
                "axis": {"range": [df_52_week_low, df_52_week_high]},
                # Set bar color to theme's primary color (extracted from previous chart)
                "bar": {"color": fig.layout.template.layout.colorway[0]},
            },
            domain={"x": [0, 1], "y": [0, 0.9]},
        )
    )

    # Plot current price
    fig2.add_trace(
        go.Indicator(
            value=current_price,
            mode="number",
            number={"valueformat": ".2f", "font_size": 27},
            domain={"x": [0.5, 0.5], "y": [0.35, 0.5]},
        )
    )

    # Plot colored percentage above the 52-week low
    fig2.add_trace(
        go.Indicator(
            value=current_price,
            mode="delta",
            delta={
                "reference": df_52_week_low,
                "relative": True,
                "valueformat": ".2%",
                "font_size": 13,
            },
            title={"text": "Above Low", "font_size": 13},
            domain={"x": [0.27, 0.37], "y": [0, 0.35]},
        )
    )

    # Plot colored percentage below the 52-week high
    fig2.add_trace(
        go.Indicator(
            value=current_price,
            mode="delta",
            delta={
                "reference": df_52_week_high,
                "relative": True,
                "valueformat": ".2%",
                "font_size": 13,
            },
            title={"text": "Below High", "font_size": 13},
            domain={"x": [0.63, 0.73], "y": [0, 0.35]},
        )
    )

    fig2.update_layout(
        template=template_from_url(theme),  # set theme
        title={"text": "52-Week High/Low Indicator", "y": 0.9},
        font_size=9,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=280,
        width=357,
        margin=dict(l=1, r=1, b=0, t=0),
        showlegend=False,
    )

    return fig, fig2
