import datetime
import threading

import pandas as pd
from dash import callback_context, dash_table, html
from dash.dependencies import Input, Output

from innov8.decorators.data_access import callback, data_access

# Store intermediate values
corrs: dict[str, pd.DataFrame] = {}
prices: dict[str, pd.DataFrame] = {}
threadlock = threading.Lock()


# This DataTable contains intra-sector ticker prices and 90-day correlations
def table_info():
    return html.Div(
        [
            html.P(
                "Intra-sector Table",
                id="intra-sector-title",
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
                style_data={"backgroundColor": "rgba(0,0,0,0)"},
                style_as_list_view=True,
            ),
        ],
        id="intra-sector-container",
    )


@data_access
def calculate_table_data(data, sector) -> None:
    """Calculate intra-sector data for `correlation-table`"""
    global corrs, prices
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
    with threadlock:
        # Pivot and calculate correlations
        corrs[sector] = (
            sector_table.pivot(columns="symbol", index="date", values="close")
            .corr()
            .round(3)
        )
        # Get prices of tickers in sector
        prices[sector] = (
            sector_table.drop(columns="date").groupby("symbol").last().round(2)
        )


# Update the table
@callback(
    Output("correlation-table", "data"),
    Input("sector-dropdown", "value"),
    Input("symbol-dropdown", "value"),
    Input("update-state", "data"),
)
def update_intra_sector_table(sector, symbol, _):
    # Only recalculate when sector changes or data is updated, not when symbol changes
    if callback_context.triggered_prop_ids != {
        "symbol-dropdown.value": "symbol-dropdown"
    }:
        calculate_table_data(sector)
    with threadlock:
        # Filter intra-sector correlation data
        filt_corr = pd.DataFrame(corrs[sector])[symbol].drop(symbol).to_frame()
        # Filter intra-sector price data
        filt_prices = pd.DataFrame(prices[sector]).drop(symbol)
    # Combine into a single table
    table = (
        filt_prices.join(filt_corr)
        .reset_index()
        .rename(columns={symbol: "90-day corr", "close": "price", "index": "symbol"})
        .sort_values(by="90-day corr", key=abs, ascending=False)
    )

    return table.to_dict("records")
