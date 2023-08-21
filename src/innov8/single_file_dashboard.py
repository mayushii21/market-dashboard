import datetime

import dash
import dash_bootstrap_components as dbc
import dash_trich_components as dtc
import pandas as pd
import plotly.graph_objects as go
from dash import Patch, callback_context, dash_table, dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash_bootstrap_templates import ThemeChangerAIO, template_from_url
from plotly.subplots import make_subplots

# import database connection object and the function for updating ohlc data
from innov8.db_ops import add_new_ohlc, con, cur

### Load main data into a pandas DataFrame
main_query = """
SELECT t.symbol,
    t.name,
    s.name sector,
    DATE(d.date, 'unixepoch') date,
    p.open,
    p.high,
    p.low,
    p.close,
    p.volume,
    e.name exchange,
    tt.name type,
    c.iso_code currency
FROM price p
    JOIN ticker t ON p.ticker_id = t.id
    JOIN date d ON p.date_id = d.id
    JOIN sector s ON t.sector_id = s.id
    JOIN exchange e ON t.exchange_id = e.id
    JOIN currency c ON t.currency_id = c.id
    JOIN ticker_type tt ON t.ticker_type_id = tt.id
"""


# Create DataFrame from SQL query
def load_main_table():
    global main_table
    main_table = pd.read_sql_query(
        main_query,
        con,
        parse_dates=["date"],
        dtype={
            "symbol": "category",
            "name": "category",
            "sector": "category",
            "exchange": "category",
            "type": "category",
            "currency": "category",
        },
    )


load_main_table()
main_table.head()
# Initiate dash app with default theme (visible for a split second before theme from ThemeChangerAIO takes over)
default_theme = dbc.themes.CYBORG
# css for styling dcc and html components with dbc themes
dbc_css = (
    "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.8/dbc.min.css"
)
app = dash.Dash(__name__, external_stylesheets=[default_theme, dbc_css])
server = app.server
change_query = """
WITH growth AS (
    SELECT t.symbol,
        d.date,
        p.close
    FROM price p
        JOIN ticker t ON p.ticker_id = t.id
        JOIN date d ON p.date_id = d.id
)
SELECT g1.symbol,
    100 * (g1.close - g2.close) / g2.close AS growth_percentage
FROM growth g1
    JOIN (
        SELECT symbol,
            MAX(date) today
        FROM growth
        GROUP BY symbol
    ) t ON g1.symbol = t.symbol
    AND g1.date = t.today
    JOIN growth g2 ON g1.symbol = g2.symbol
    AND g2.date = (
        SELECT MAX(date)
        FROM growth
        WHERE symbol = g1.symbol
            AND date < g1.date
    )
ORDER BY ABS(growth_percentage) DESC
LIMIT 10
"""
# list all sectors
sector_query = """
SELECT name
FROM sector
ORDER BY name
"""
cur.execute(sector_query).fetchmany(3)
# list ticker symbols in sector
symbols_query = """
SELECT symbol
FROM ticker t
    JOIN sector s ON s.id = t.sector_id
WHERE s.name = ?
ORDER BY symbol
"""
cur.execute(symbols_query, ("Technology",)).fetchmany(3)
# Accepts a list of elements (list comp of html divs in this case) to "carouse" through
carousel = dtc.Carousel(
    [
        html.Div(
            [
                # Ticker symbol
                html.Span(symbol, style={"marginRight": "10px"}),
                # Change (colored)
                html.Span(
                    f"{'+' if change > 0 else ''}{change:.2f}%",
                    style={"color": "green" if change > 0 else "red"},
                ),
            ]
        )
        for symbol, change in cur.execute(change_query)
    ],
    id="main-carousel",
    autoplay=True,
    speed=500,
    slides_to_show=5,
    responsive=[{"breakpoint": 9999, "settings": {"arrows": False}}],
)


# Update with new ohlc data on button press
@app.callback(
    Output("main-carousel", "children"),
    Input("update-state", "data"),
)
def update_ticker_data(update):
    return [
        html.Div(
            [
                # Ticker symbol
                html.Span(symbol, style={"marginRight": "10px"}),
                # Change (colored)
                html.Span(
                    f"{'+' if change > 0 else ''}{change:.2f}%",
                    style={"color": "green" if change > 0 else "red"},
                ),
            ]
        )
        for symbol, change in cur.execute(change_query)
    ]


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


# Store intermediate values
# Data with the session option will survive a page refresh but will be forgotten on page close
intra_sector_data = dcc.Store(id="intra_sector_data", storage_type="session")


# Calculate intra-sector data for "correlation-table", update when sector changes or data is updated
@app.callback(
    Output("intra_sector_data", "data"),
    Input("sector-dropdown", "value"),
    Input("update-state", "data"),
)
def calculate_table_data(sector, update):
    # Filter by sector and select necessary columns
    sector_table = main_table.loc[
        main_table.sector == sector, ["symbol", "date", "close"]
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
        add_new_ohlc(symbol)
        up_to_date[symbol] = True
    elif scope == "Sector":
        for symbol in sector_symbols:
            add_new_ohlc(symbol)
        up_to_date[sector] = True
    else:
        for symbol in main_table.symbol.unique():
            add_new_ohlc(symbol)
        up_to_date["All"] = True
    # Reload the main_table
    load_main_table()
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


# The price (candlestick) chart
price_chart = dcc.Graph(id="price-chart")
# EMA switch with selectable period
ema = dbc.InputGroup(
    [
        dbc.InputGroupText(
            dbc.Checklist(["EMA"], id="ema", switch=True, persistence=True),
            style={
                "height": "37px",
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
            },
            class_name="btn btn-outline-secondary",
        ),
        dbc.Input(
            id="ema-period",
            placeholder="Period",
            type="number",
            min=1,
            max=200,
            step=1,
            value=9,
            persistence=True,
            style={"paddingLeft": 10},
        ),
    ],
)

# SMA switch with selectable period
sma = dbc.InputGroup(
    [
        dbc.InputGroupText(
            dbc.Checklist(["SMA"], id="sma", switch=True, persistence=True),
            style={
                "height": "37px",
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
            },
            class_name="btn btn-outline-secondary",
        ),
        dbc.Input(
            id="sma-period",
            placeholder="Period",
            type="number",
            min=1,
            max=200,
            step=1,
            value=50,
            persistence=True,
            style={"paddingLeft": 10},
        ),
    ],
)


# Update price chart (with indicators)
@app.callback(
    Output("price-chart", "figure"),
    Input("symbol-dropdown", "value"),
    Input("ema", "value"),
    Input("sma", "value"),
    State("ema-period", "value"),
    State("sma-period", "value"),
    Input(ThemeChangerAIO.ids.radio("theme"), "value"),
    Input("update-state", "data"),
)
def update_price_chart(symbol, ema, sma, ema_period, sma_period, theme, update):
    # Filter data by ticker symbol
    ticker = main_table[main_table.symbol == symbol].set_index("date")
    green = "#079A80"
    red = "#F23645"
    # Add color for plotting
    ticker["color"] = green
    ticker["color"] = ticker.color.where(ticker["close"] > ticker["open"], red).astype(
        "category"
    )
    # Each indicator will have its own color in the chart
    colors = {"SMA": "#1c90d4", "EMA": "#ad0026"}

    # Create figure with secondary y-axis (for the Volume chart)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Plot candlesticks (price)
    fig.add_trace(
        go.Candlestick(
            x=ticker.index,
            open=ticker.open,
            high=ticker.high,
            low=ticker.low,
            close=ticker.close,
            name="Price",
            increasing_line_color=green,
            decreasing_line_color=red,
        ),
        secondary_y=True,
    )

    # Plot bar chart (volume)
    fig.add_trace(
        go.Bar(
            x=ticker.index,
            y=ticker.volume,
            name="Volume",
            marker_color=ticker.color,
            marker_opacity=0.5,
        ),
        secondary_y=False,
    )

    # Select latest date for specifying default range
    latest_date = ticker.index[-1]
    fig.update_layout(
        template=template_from_url(theme),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, b=7, t=7),
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(
            showgrid=False,
            range=[
                latest_date - datetime.timedelta(180),
                # ticker.index[-1] - relativedelta(months=6),
                latest_date + datetime.timedelta(1),
            ],  # default plot range - 180 days before latest update
            rangeslider=dict(visible=True, bgcolor="rgba(0,0,0,0)"),
            rangebreaks=[
                dict(bounds=["sat", "mon"]),  # hide weekends
                # dict(values=["2015-12-25", "2016-01-01"])  # hide Christmas and New Year's
            ],
            rangeselector=dict(
                bgcolor="rgba(0,0,0,0)",
                buttons=list(
                    [
                        dict(count=1, label="1M", step="month", stepmode="backward"),
                        dict(count=3, label="3M", step="month", stepmode="backward"),
                        dict(count=6, label="6M", step="month", stepmode="backward"),
                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                        dict(count=1, label="1Y", step="year", stepmode="backward"),
                        dict(step="all"),
                    ]
                ),
            ),
            # type="date",
        ),
        yaxis=dict(
            visible=False,
            showgrid=False,
            range=[0, ticker.volume.max() * 4],
            # scaleanchor="y2",
            # scaleratio=0.0000001,
            # constraintoward="bottom",
            rangemode="tozero",
        ),
        yaxis2=dict(
            showgrid=False,
            # tickprefix="$"
        ),
    )

    def plot_line(indicator):
        # Plot indicator
        fig.add_trace(
            go.Scatter(
                x=ticker.index,
                y=ticker[indicator],
                name=indicator,
                mode="lines",
                line={
                    "color": colors[indicator],
                    "width": 3,
                },
                opacity=0.7,
            ),
            secondary_y=True,
        )

    # Empty list check
    if ema:
        ticker["EMA"] = (
            ticker["close"]
            .ewm(span=ema_period, min_periods=ema_period, adjust=False)
            .mean()
        )
        plot_line("EMA")
    if sma:
        ticker["SMA"] = ticker["close"].rolling(window=sma_period).mean()
        plot_line("SMA")

    return fig


# Update indicators using partial property assignment
@app.callback(
    Output("price-chart", "figure", allow_duplicate=True),
    State("price-chart", "figure"),
    State("ema", "value"),
    State("sma", "value"),
    Input("ema-period", "value"),
    Input("sma-period", "value"),
    prevent_initial_call=True,
)
def update_indicator_period(fig, ema, sma, ema_period, sma_period):
    # If no indicator is selected - prevent update
    if not (ema or sma):
        raise PreventUpdate
    # Store subplot indexes for accessing appropriate data
    fig_index = {fig["data"][i]["name"]: i for i in range(len(fig["data"]))}
    # Creating a Patch object
    patched_figure = Patch()
    # Update partial property (y data for indicator)
    if callback_context.triggered_id == "ema-period" and ema:
        patched_figure.data[fig_index[ema[0]]].y = (
            ticker["close"]
            .ewm(span=ema_period, min_periods=ema_period, adjust=False)
            .mean()
        )
    if callback_context.triggered_id == "sma-period" and sma:
        patched_figure.data[fig_index[sma[0]]].y = (
            ticker["close"].rolling(window=sma_period).mean()
        )

    return patched_figure


# div with main ticker information
price_card = html.Div(
    [
        # Symbol
        html.H4(
            id="ticker-symbol",
            style={
                "textAlign": "left",
                "marginTop": 10,
                "marginBottom": -7,
            },
        ),
        # Name
        html.P(
            id="ticker-name",
            style={
                "fontSize": "12px",
                "textAlign": "left",
                "marginBottom": -7,
            },
        ),
        # Price and currency
        html.P(
            id="ticker-price",
            style={
                "fontSize": "27px",
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
                "fontSize": "14px",
                "marginBottom": -3,
            },
        ),
        # Economic sector
        html.P(
            id="economic-sector",
            style={
                "textAlign": "left",
                "fontSize": "14px",
            },
        ),
    ],
    id="ticker-data",
    style={"height": "140px"},
)


# The following function will edit the values being displayed in the "ticker-data" Div
@app.callback(
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
def update_symbol_data(symbol, update):
    ticker = main_table.loc[
        main_table.symbol == symbol, ["name", "close", "exchange", "sector", "currency"]
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
            "fontSize": "14px",
            "textAlign": "right",
            "marginBottom": -3,
            "color": "green" if change > 0 else "red",
        },  # set style color depending on price change
        f"Exchange: {ticker.iat[0, 2]}",
        f"Sector: {ticker.iat[0, 3]}",
    )


# This DataTable contains intra-sector ticker prices and 90-day correlations
table_info = html.Div(
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
            style_table={"height": "100px", "overflowY": "auto"},
            style_as_list_view=True,
        ),
    ]
)


# Update the table
@app.callback(
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


# Carousel showing 52-week data
carousel_52_week = dtc.Carousel(
    [
        dcc.Graph(id="52-week-price-chart"),
        dcc.Graph(id="52-week-high-low-indicator"),
    ],
    slides_to_show=1,
    vertical=True,
    autoplay=True,
    speed=3000,
    style={
        "height": 230,
        "width": 290,
    },
    responsive=[
        {"breakpoint": 9999, "settings": {"arrows": False}},
    ],
)


# This function is responsible for updating the weekly price chart and the gauge (speedometer) chart
@app.callback(
    Output("52-week-price-chart", "figure"),
    Output("52-week-high-low-indicator", "figure"),
    Input("symbol-dropdown", "value"),
    Input(ThemeChangerAIO.ids.radio("theme"), "value"),
    Input("update-state", "data"),
)
def update_52_week_charts(symbol, theme, update):
    # Filter data by ticker symbol
    ticker = main_table[main_table.symbol == symbol].set_index("date")

    # The output from this resample operation feeds the weekly closing price chart
    weekly_52 = (
        ticker.resample(
            "W-MON",
            closed="left",
            label="left",
        )["close"]
        .last()
        .iloc[-52:]
    )

    # Plot 52 week chart (price)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=weekly_52.index,
            y=weekly_52.values,
            line_width=3,
        )
    )
    fig.update_layout(
        template=template_from_url(theme),  # set theme
        title={"text": "Weekly Chart", "y": 0.9},
        font_size=9,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=230,
        width=290,
        margin=dict(l=1, r=1, b=0, t=0),
        showlegend=False,
    )
    fig.update_xaxes(showticklabels=False, showgrid=False)
    fig.update_yaxes(showticklabels=False, showgrid=False)

    # Get 52-week low/high and current price
    df_52_week_low = ticker.close[-252:].min()
    df_52_week_high = ticker.close[-252:].max()
    current_price = ticker.iat[-1, ticker.columns.get_loc("close")]

    # Plot gauge (speedometer) chart which indicates the tickers current price compared to it's 52-week high/low
    fig2 = go.Figure()
    fig2.add_trace(
        go.Indicator(
            value=current_price,
            mode="gauge",
            gauge={
                "axis": {"range": [df_52_week_low, df_52_week_high]},
                # Set bar color to theme's primary color (extracted from previous chart)
                "bar": {"color": fig.layout.template.layout.colorway[0]},
            },
            domain={"x": [0, 1], "y": [0, 0.9]},
        )
    )

    # Plot current price
    fig2.add_trace(
        go.Indicator(
            value=current_price,
            mode="number",
            number={"valueformat": ".2f", "font_size": 27},
            domain={"x": [0.5, 0.5], "y": [0.35, 0.5]},
        )
    )

    # Plot colored percentage above the 52-week low
    fig2.add_trace(
        go.Indicator(
            value=current_price,
            mode="delta",
            delta={
                "reference": df_52_week_low,
                "relative": True,
                "valueformat": ".2%",
                "font_size": 13,
            },
            title={"text": "Above Low", "font_size": 13},
            domain={"x": [0.27, 0.37], "y": [0, 0.35]},
        )
    )

    # Plot colored percentage below the 52-week high
    fig2.add_trace(
        go.Indicator(
            value=current_price,
            mode="delta",
            delta={
                "reference": df_52_week_high,
                "relative": True,
                "valueformat": ".2%",
                "font_size": 13,
            },
            title={"text": "Below High", "font_size": 13},
            domain={"x": [0.63, 0.73], "y": [0, 0.35]},
        )
    )

    fig2.update_layout(
        template=template_from_url(theme),  # set theme
        title={"text": "52-Week High/Low Indicator", "y": 0.9},
        font_size=9,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=230,
        width=290,
        margin=dict(l=1, r=1, b=0, t=0),
        showlegend=False,
    )

    return fig, fig2


theme_changer = ThemeChangerAIO(
    aio_id="theme",
    radio_props={
        "options": [
            {
                "label": "Cyborg",
                "value": dbc.themes.CYBORG,
                "label_id": "theme-switch-label-dark",
            },
            {
                "label": "Darkly",
                "value": dbc.themes.DARKLY,
                "label_id": "theme-switch-label-dark",
            },
            {
                "label": "Slate",
                "value": dbc.themes.SLATE,
                "label_id": "theme-switch-label-dark",
            },
            {
                "label": "Solar",
                "value": dbc.themes.SOLAR,
                "label_id": "theme-switch-label-dark",
            },
            {
                "label": "Superhero",
                "value": dbc.themes.SUPERHERO,
                "label_id": "theme-switch-label-dark",
            },
            {
                "label": "Vapor",
                "value": dbc.themes.VAPOR,
                "label_id": "theme-switch-label-dark",
            },
            {
                "label": "Bootstrap",
                "value": dbc.themes.BOOTSTRAP,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Flatly",
                "value": dbc.themes.FLATLY,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Journal",
                "value": dbc.themes.JOURNAL,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Lumen",
                "value": dbc.themes.LUMEN,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Minty",
                "value": dbc.themes.MINTY,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Simplex",
                "value": dbc.themes.SIMPLEX,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Spacelab",
                "value": dbc.themes.SPACELAB,
                "label_id": "theme-switch-label",
            },
            {
                "label": "United",
                "value": dbc.themes.UNITED,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Yeti",
                "value": dbc.themes.YETI,
                "label_id": "theme-switch-label",
            },
        ],
        "value": dbc.themes.CYBORG,
        "persistence": True,
    },
    button_props={"style": {"height": "37px"}},
)

app.layout = dbc.Container(
    [
        # A carousel for 10 tickers with the largest absolute change occupies the topmost row
        dbc.Row([dbc.Col([carousel], width=12)]),
        dbc.Row(
            [
                # This first column occupies 75% of the dashboard's width
                dbc.Col(
                    [
                        # This row holds the dropdowns responsible for sector and ticker selection and the update button
                        dbc.Row(
                            [
                                dbc.Col([dropdown_1], width=5),
                                dbc.Col([dropdown_2], width=3),
                                dbc.Col(
                                    [
                                        dcc.Loading(
                                            [update_button, update_state], type="dot"
                                        )
                                    ],
                                    width=3,
                                ),
                            ],
                            class_name="mb-1",
                        ),
                        # This row contains the main price (candlestick) chart
                        dbc.Row(
                            [
                                dbc.Col(
                                    [dcc.Loading(price_chart, type="circle")], width=12
                                ),
                            ],
                        ),
                        # This row stores the theme changer component and indicators
                        dbc.Row(
                            [
                                dbc.Col(theme_changer, width=2),
                                dbc.Col(ema, width={"size": 4, "offset": 1}),
                                dbc.Col(sma, width=4),
                            ],
                            class_name="mb-1",
                        ),
                    ],
                    width=9,
                ),
                # This column occupies 25% of the dashboard's width
                dbc.Col(
                    [
                        dbc.Row([dbc.Col([price_card], width=12)]),
                        dbc.Row([dbc.Col([table_info], width=12)]),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [dcc.Loading(carousel_52_week, type="circle")],
                                    width=12,
                                )
                            ],
                        ),
                    ],
                    width=3,
                ),
            ],
            class_name="g-0",  # remove gutters
        ),
        intra_sector_data,
    ],
    fluid=True,
    class_name="dbc",
    style={"height": "100%", "width": "100%", "margin": 0, "overflow": "hidden"},
)


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
