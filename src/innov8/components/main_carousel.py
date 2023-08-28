import dash_trich_components as dtc
from dash import html
from dash.dependencies import Input, Output

from innov8.components.decorators import callback, data_access

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


# Accepts a list of elements (list comp of html divs in this case) to "carouse" through
@data_access
def carousel(data):
    return dtc.Carousel(
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
            for symbol, change in data.cur.execute(change_query)
        ],
        id="main-carousel",
        autoplay=True,
        speed=500,
        slides_to_show=5,
        responsive=[{"breakpoint": 9999, "settings": {"arrows": False}}],
    )


# Update with new ohlc data on button press
@callback(
    Output("main-carousel", "children"),
    Input("update-state", "data"),
)
@data_access
def update_main_carousel(data, update):
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
        for symbol, change in data.cur.execute(change_query)
    ]
