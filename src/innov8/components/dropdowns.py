from dash import dcc
from dash.dependencies import Input, Output

from innov8.db_ops import cur
from innov8.server import app

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
dropdown_1 = dcc.Dropdown(
    options=[sector[0] for sector in cur.execute(sector_query)],
    value="Technology",
    id="sector-dropdown",
    style={"height": "37px"},
    # placeholder="Select Economic Sector",
    clearable=False,
    persistence=True,  # user interaction local persistence
)
# The symbols dropdown
dropdown_2 = dcc.Dropdown(
    # options will be filled by callback
    # Default ticker - first ticker of sector, chosen by callback
    id="symbol-dropdown",
    style={"height": "37px"},
    # placeholder="Select Ticker Symbol",
    clearable=False,
    persistence=True,  # user interaction local persistence
)


# Update symbols dropdown with tickers from the selected sector and select first value as default
@app.callback(
    Output("symbol-dropdown", "options"),
    Output("symbol-dropdown", "value"),
    Input("sector-dropdown", "value"),
)
def update_symbols_dropdown(sector):
    # Select ticker symbols from selected sector
    options = [symbol[0] for symbol in cur.execute(symbols_query, (sector,))]
    return options, options[0]
