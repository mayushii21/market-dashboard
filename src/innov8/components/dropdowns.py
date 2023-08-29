from dash import dcc
from dash.dependencies import Input, Output

from innov8.components.decorators import callback, data_access

# list all sectors
sector_query = """
SELECT name
FROM sector
ORDER BY name
"""
# list ticker symbols in sector
symbols_query = """
SELECT symbol
FROM ticker t
    JOIN sector s ON s.id = t.sector_id
WHERE s.name = ?
ORDER BY symbol
"""


# The economic sectors dropdown
@data_access
def dropdown_1(data):
    return dcc.Dropdown(
        options=[sector[0] for sector in data.cur.execute(sector_query)],
        value="Technology",
        id="sector-dropdown",
        style={"height": "37px"},
        # placeholder="Select Economic Sector",
        clearable=False,
        persistence=True,  # user interaction local persistence
    )


# The symbols dropdown
def dropdown_2():
    return dcc.Dropdown(
        # options will be filled by callback
        # Default ticker - first ticker of sector, chosen by callback
        id="symbol-dropdown",
        style={"height": "37px"},
        # placeholder="Select Ticker Symbol",
        clearable=False,
        persistence=True,  # user interaction local persistence
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
    options = [symbol[0] for symbol in data.cur.execute(symbols_query, (sector,))]
    return options, options[0]
