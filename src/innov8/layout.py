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
    intra_sector_data,
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
            initial_load(),
            # A carousel for 10 tickers with the largest absolute change occupying the topmost row
            dbc.Row([dbc.Col([carousel()], width=12)]),
            dbc.Row(
                [
                    # This first column occupies all available width - 370px (for the second column)
                    dbc.Col(
                        [
                            # This row holds the dropdowns responsible for sector and ticker selection and the update button
                            dbc.Row(
                                [
                                    dbc.Col([dropdown_1()], width=4),
                                    dbc.Col([dropdown_2()], width=3),
                                    dbc.Col(
                                        [
                                            dcc.Loading(
                                                [update_button(), update_state()],
                                                type="dot",
                                            )
                                        ],
                                        width={"size": 3},
                                    ),
                                    dbc.Col([forecast_button()], width=1),
                                ],
                                class_name="mb-1 g-0",
                                justify="between",
                            ),
                            # This row contains the main price (candlestick) chart
                            html.Div(
                                price_chart(),
                                id="price-chart-container",
                            ),
                            # This row stores the theme changer component and indicators
                            dbc.Row(
                                [
                                    dbc.Col(theme_changer, width=2),
                                    # dbc.Col(
                                    #     dbc.DropdownMenu(
                                    #         children=[
                                    #             ema_switch(),
                                    #             sma_switch(),
                                    #         ],
                                    #         label="Technical Indicators",
                                    #         id="indicators",
                                    #         direction="up",
                                    #         align_end=True,
                                    #         color="transparent",
                                    #         style={"height": "37px", "all": "unset"},
                                    #     ),
                                    #     width="auto",
                                    # ),
                                    dbc.Col(
                                        ema_switch(), width={"size": 3, "offset": 3}
                                    ),
                                    dbc.Col(sma_switch(), width=3),
                                ],
                                justify="between",
                                class_name="mb-1 g-0",
                            ),
                        ],
                        width=9,  # investigate why this is needed later
                        style={"width": "calc(100% - 370px)"},
                    ),
                    # This column occupies 370px of the dashboard's width
                    dbc.Col(
                        [
                            dbc.Row([dbc.Col([price_card()], width=12)]),
                            dbc.Row([dbc.Col([table_info()], width=12)]),
                            html.Div(
                                carousel_52_week(),
                                id="52-week-chart-container",
                            ),
                        ],
                        width=3,  # -''-
                        style={"width": "370px"},
                    ),
                ],
                # class_name="g-0",  # remove gutters
            ),
            intra_sector_data(),
        ],
        fluid=True,
        class_name="dbc",
        style={"height": "100%", "width": "100%", "margin": 0, "overflow": "hidden"},
    )


app.layout = layout
