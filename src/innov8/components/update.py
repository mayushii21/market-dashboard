import dash_bootstrap_components as dbc
from dash import dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from tqdm import tqdm

from innov8.components.decorators import callback, data_access


# Button with scope dropdown
def update_button():
    return dbc.ButtonGroup(
        [
            dbc.Button(
                id="update-button",
                outline=True,
                style={
                    "height": "37px",
                    "width": "140px",
                    "display": "flex",
                    "justifyContent": "center",
                    "alignItems": "center",
                },
            ),
            dcc.Dropdown(
                options=["Ticker", "Sector", "All"],
                value="Ticker",
                id="update-dropdown",
                style={
                    "width": "70%",
                    "height": "37px",
                    "border-top-left-radius": 0,  # squarify :]
                    "border-bottom-left-radius": 0,
                },
                clearable=False,
            ),
        ],
        # style={"padding-left": "4em", "margin-left": "auto", "margin-right": 0},
        style={"width": "100%"},
    )


# Store update state
# Data with the session option will survive a page refresh but will be forgotten on page close
def update_state():
    return dcc.Store(id="update-state", data={}, storage_type="session")


# Update with new ohlc data on button press
@callback(
    Output("update-state", "data"),
    Input("update-button", "n_clicks"),
    State("update-dropdown", "value"),
    State("symbol-dropdown", "value"),
    State("symbol-dropdown", "options"),
    State("sector-dropdown", "value"),
    State("update-state", "data"),
)
@data_access
def update_ticker_data(data, button, scope, symbol, sector_symbols, sector, up_to_date):
    # Prevent the initial callback to avoid updating the store for nothing
    if button is None:
        raise PreventUpdate
    # Add new data for the chosen scope and update the update-state
    if scope == "Ticker":
        print(f"Updating {symbol}...", end=" ", flush=True)
        data.add_new_ohlc(symbol)
        up_to_date[symbol] = True
        print("success ✓")
    elif scope == "Sector":
        print("Updating sector...")
        for symbol in tqdm(sector_symbols):
            data.add_new_ohlc(symbol)
        up_to_date[sector] = True
    else:
        print("Updating all...")
        for symbol in tqdm(data.main_table.symbol.unique()):
            data.add_new_ohlc(symbol)
        up_to_date["All"] = True
    # Reload the main_table
    data.load_main_table()
    return up_to_date


# Update the style of the update button
@callback(
    Output("update-button", "children"),
    Output("update-button", "color"),
    Output("update-button", "disabled"),
    Input("update-dropdown", "value"),
    Input("symbol-dropdown", "value"),
    State("sector-dropdown", "value"),
    Input("update-state", "data"),
)
def update_button_style(scope, symbol, sector, up_to_date):
    # Set color to "success" and disable if updated, else set "info" and enabled
    if (
        (scope == "Ticker" and symbol in up_to_date)
        or (scope in ["Ticker", "Sector"] and sector in up_to_date)
        or "All" in up_to_date
    ):
        return "Up to date", "success", True
    else:
        return "Update", "info", False
