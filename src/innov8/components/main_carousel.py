from dash import html
from dash.dependencies import Input, Output, State

from innov8.decorators.data_access import callback, clientside_callback, data_access

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


def carousel() -> html.Div:
    return html.Div(
        html.Div(
            className="swiper-wrapper",
            id="main-carousel",
        ),
        className="swiper mainSwiper",
    )


# Update with new ohlc data on button press
@callback(
    Output("main-carousel", "children"),
    Input("update-state", "data"),
)
@data_access
def update_main_carousel(data, _) -> list[html.Div]:
    return [
        html.Div(
            [
                # Ticker symbol
                html.Span(symbol),
                # Change (colored)
                html.Span(
                    f"{'+' if change > 0 else ''}{change:.2f}%",
                    style={
                        "margin-left": "10px",
                        "color": "green" if change > 0 else "red",
                    },
                ),
            ],
            className="swiper-slide",
        )
        for symbol, change in data.cur.execute(change_query)
    ]


clientside_callback(
    """
    function initializeMainSwiper(id) {
        function initSwiper() {
            var swiper = new Swiper(".mainSwiper", {
                slidesPerView: 2,
                breakpoints: {
                    // when window width is >= 768px
                    768: {
                    slidesPerView: 5,
                    spaceBetween: 40
                    }
                },
                loop: true,
                autoplay: {
                    delay: 2000,
                    disableOnInteraction: false,
                },
                observer: true,
                cssMode: true,
            });
        }

        // Polling mechanism to check if #main-carousel has children
        const checkChildren = setInterval(() => {
            const carouselElement = document.getElementById("main-carousel");

            // Check if the carousel element exists and has children
            if (carouselElement && carouselElement.children.length > 0) {
                clearInterval(checkChildren); // Stop polling once children are found
                initSwiper(); // Initialize Swiper
            }
        }, 100); // Check every 100 milliseconds

        return window.dash_clientside.no_update;
    }
    """,
    Output("main-carousel", "id"),
    Input("initial-load", "className"),
    State("main-carousel", "children"),
)
