import dash_bootstrap_components as dbc
from dash import dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from innov8.app import app
from innov8.db_ops import data

# Button with scope dropdown
update_button = dbc.ButtonGroup(
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
        # dbc.DropdownMenu(
        #     [dbc.DropdownMenuItem("Ticker"), dbc.DropdownMenuItem("All")],
        #     label="Update Scope",
        #     group=True,
        # ),
        dcc.Dropdown(
            options=["Ticker", "Sector", "All"],
            value="Ticker",
            id="update-dropdown",
            style={"width": "8vw", "height": "37px"},
            clearable=False,
        ),
    ]
)

# Store update state
# Data with the session option will survive a page refresh but will be forgotten on page close
update_state = dcc.Store(id="update-state", data={}, storage_type="session")


### *Note here for future experiments* (loading component)
# Update with new ohlc data on button press
@app.callback(
    Output("update-state", "data"),
    Input("update-button", "n_clicks"),
    State("update-dropdown", "value"),
    State("symbol-dropdown", "value"),
    State("symbol-dropdown", "options"),
    State("sector-dropdown", "value"),
    State("update-state", "data"),
)
def update_ticker_data(button, scope, symbol, sector_symbols, sector, up_to_date):
    # Prevent the initial callback to avoid updating the store for nothing
    if button is None:
        raise PreventUpdate
    # Add new data for the chosen scope and update the update-state
    if scope == "Ticker":
        data.add_new_ohlc(symbol)
        up_to_date[symbol] = True
    elif scope == "Sector":
        for symbol in sector_symbols:
            data.add_new_ohlc(symbol)
        up_to_date[sector] = True
    else:
        for symbol in data.main_table.symbol.unique():
            data.add_new_ohlc(symbol)
        up_to_date["All"] = True
    # Reload the main_table
    data.load_main_table()
    return up_to_date


# Update the style of the update button
@app.callback(
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
