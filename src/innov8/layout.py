import dash_bootstrap_components as dbc
from dash import dcc, html

from innov8.app import app
from innov8.components import (
    carousel,
    carousel_52_week,
    dropdown_1,
    dropdown_2,
    ema_switch,
    forecast_button,
    initial_load,
    price_card,
    price_chart,
    sma_switch,
    table_info,
    theme_changer,
    update_button,
    update_state,
)
from innov8.db_ops import data


# Pool (combine) the layout
def layout() -> dbc.Container:
    # update main table only if needed (update signal exists)
    data.load_main_table(force_update=False)
    return dbc.Container(
        [
            # A carousel for 10 tickers with the largest absolute change occupying the topmost row
            carousel(),
            dropdown_1(),
            dropdown_2(),
            html.Div(
                dcc.Loading(
                    [update_button(), update_state()],
                    type="dot",
                ),
                id="update-button-container",
            ),
            forecast_button(),
            html.Div(
                price_chart(),
                id="price-chart-container",
                className="invisible",  # hidden on initial load
            ),
            # This row stores the theme changer component and indicators
            theme_changer,
            ema_switch(),
            sma_switch(),
            price_card(),
            table_info(),
            html.Div(
                carousel_52_week(),
                id="weekly-charts-container",
                hidden=True,  # hidden on initial load
            ),
            initial_load(),
            html.Div(className="blur top row-option"),
            html.Div(className="blur bottom row-option"),
        ],
        fluid=True,
        className="dbc grid-container",
    )


app.layout = layout
