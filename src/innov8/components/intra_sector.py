import datetime

import pandas as pd
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output

from innov8.components.decorators import callback, data_access


# Store intermediate values
# Data with the session option will survive a page refresh but will be forgotten on page close
def intra_sector_data():
    return dcc.Store(id="intra_sector_data", storage_type="session")


# Calculate intra-sector data for "correlation-table", update when sector changes or data is updated
@callback(
    Output("intra_sector_data", "data"),
    Input("sector-dropdown", "value"),
    Input("update-state", "data"),
)
@data_access
def calculate_table_data(data, sector, update):
    # Filter by sector and select necessary columns
    sector_table = data.main_table.loc[
        data.main_table.sector == sector, ["symbol", "date", "close"]
    ]
    # Convert to string from category
    sector_table["symbol"] = sector_table.symbol.astype(str)
    # Find the latest date that is shared by all symbols of the sector
    end_date = sector_table.groupby("symbol").date.max().min()
    # Subtract 90 days
    start_date = end_date - datetime.timedelta(90)
    # Filter the date
    sector_table = sector_table[
        (sector_table.date >= start_date) & (sector_table.date <= end_date)
    ]
    # Pivot and calculate correlations
    intra_sector_corr = (
        sector_table.pivot(columns="symbol", index="date", values="close")
        .corr()
        .round(3)
    )
    # Get prices of tickers in sector
    sector_prices = sector_table.drop(columns="date").groupby("symbol").last().round(2)

    return [intra_sector_corr.to_dict(), sector_prices.to_dict()]


# This DataTable contains intra-sector ticker prices and 90-day correlations
def table_info():
    return html.Div(
        [
            html.Label(
                "Intra-sector Data Table",
                style={"textAlign": "center", "display": "block"},
            ),
            dash_table.DataTable(
                id="correlation-table",
                style_cell={
                    "font_size": "12px",
                    "textAlign": "right",
                    "padding-right": "7px",
                },
                style_cell_conditional=[
                    {
                        "if": {"column_id": "symbol"},
                        "textAlign": "left",
                        "padding-left": "7px",
                    },
                    {"if": {"column_id": ["price", "90-day corr"]}, "width": "30%"},
                ],
                style_header={"backgroundColor": "rgba(0,0,0,0)"},
                style_data={"backgroundColor": "rgba(0,0,0,0)"},
                style_table={"height": "180px", "overflowY": "auto"},
                style_as_list_view=True,
            ),
        ]
    )


# Update the table
@callback(
    Output("correlation-table", "data"),
    Input("symbol-dropdown", "value"),
    Input("intra_sector_data", "data"),
)
def update_intra_sector_table(symbol, data):
    # Filter intra-sector correlation data
    filt_corr = pd.DataFrame(data[0])[symbol].drop(symbol).to_frame()
    # Filter intra-sector price data
    filt_prices = pd.DataFrame(data[1]).drop(symbol)
    # Combine into a single table
    table = (
        filt_prices.join(filt_corr)
        .reset_index()
        .rename(columns={symbol: "90-day corr", "close": "price", "index": "symbol"})
        .sort_values(by="90-day corr", key=abs, ascending=False)
    )
    return table.to_dict("records")
