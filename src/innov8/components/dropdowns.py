from dash import dcc
from dash.dependencies import Input, Output

from innov8.decorators.data_access import callback, data_access


# The economic sectors dropdown
@data_access
def dropdown_1(data):
    return dcc.Dropdown(
        options=sorted(data.main_table["sector"].unique().tolist()),
        value="Technology",
        id="sector-dropdown",
        searchable=False,
        clearable=False,
        persistence=True,  # user interaction local persistence
        className="row-option",
    )


# The symbols dropdown
def dropdown_2():
    return dcc.Dropdown(
        # options will be filled by callback
        # Default ticker - first ticker of sector, chosen by callback
        id="symbol-dropdown",
        searchable=False,
        clearable=False,
        persistence=True,  # user interaction local persistence
        className="row-option",
    )


# Update symbols dropdown with tickers from the selected sector and select first value as default
@callback(
    Output("symbol-dropdown", "options"),
    Output("symbol-dropdown", "value"),
    Input("sector-dropdown", "value"),
)
@data_access
def update_symbols_dropdown(data, sector):
    # Select ticker symbols from selected sector
    options = sorted(
        data.main_table.loc[data.main_table["sector"] == sector, "symbol"]
        .unique()
        .tolist()
    )
    return options, options[0]
