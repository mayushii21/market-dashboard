from dash import html
from dash.dependencies import Input, Output

from innov8.components.decorators import callback, data_access


# div with main ticker information
def price_card():
    return html.Div(
        [
            # Symbol
            html.H2(
                id="ticker-symbol",
                style={
                    "textAlign": "left",
                    "marginTop": 0,
                    "marginBottom": -7,
                },
            ),
            # Name
            html.P(
                id="ticker-name",
                style={
                    "fontSize": "14px",
                    "textAlign": "left",
                    "marginBottom": -7,
                },
            ),
            # Price and currency
            html.P(
                id="ticker-price",
                style={
                    "fontSize": "33px",
                    "textAlign": "right",
                    "marginBottom": -7,
                },
            ),
            # Price change (style is specified in callback)
            html.P(
                id="ticker-change",
            ),
            # Exchange
            html.P(
                id="exchange-name",
                style={
                    "textAlign": "left",
                    "fontSize": "19px",
                    "marginBottom": -3,
                },
            ),
            # Economic sector
            html.P(
                id="economic-sector",
                style={
                    "textAlign": "left",
                    "fontSize": "19px",
                },
            ),
        ],
        id="ticker-data",
        style={"height": "190px"},
    )


# The following function will edit the values being displayed in the "ticker-data" Div
@callback(
    Output("ticker-symbol", "children"),
    Output("ticker-name", "children"),
    Output("ticker-price", "children"),
    Output("ticker-change", "children"),
    Output("ticker-change", "style"),
    Output("exchange-name", "children"),
    Output("economic-sector", "children"),
    Input("symbol-dropdown", "value"),
    Input("update-state", "data"),
)
@data_access
def update_symbol_data(data, symbol, update):
    ticker = data.main_table.loc[
        data.main_table.symbol == symbol,
        ["name", "close", "exchange", "sector", "currency"],
    ].tail(2)
    # Getting the chosen symbol's current price and its change in comparison to its previous value
    current_price = ticker.iat[-1, 1]
    change = (current_price / ticker.iat[-2, 1]) - 1
    return (
        symbol,
        ticker.iat[0, 0],  # ticker name
        f"{current_price:.2f} ({ticker.iat[0, 4]})",  # (currency)
        f"{'+' if change > 0 else ''}{change:.2%}",
        {
            "fontSize": "17px",
            "textAlign": "right",
            "marginBottom": -3,
            "color": "green" if change > 0 else "red",
        },  # set style color depending on price change
        f"Exchange: {ticker.iat[0, 2]}",
        f"Sector: {ticker.iat[0, 3]}",
    )
