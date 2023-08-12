import sqlite3
import yfinance as yf

# Connect to database
con = sqlite3.connect("stonks.db", check_same_thread=False)
cur = con.cursor()
ticker_symbols = [
    symbol[0]
    for symbol in con.execute(
        """
        SELECT symbol
        FROM ticker
        """
    ).fetchall()
]

# Initiate tickers instance
tickers = yf.Tickers(" ".join(ticker_symbols[:30]))


# Define function for updating ohlc data for a given ticker by it's symbol
def add_new_ohlc(symbol):
    try:
        # Get date for latest entry
        latest_entry = cur.execute(
            """
            SELECT DATE(max(date) + 86400, 'unixepoch')
            FROM price p
                JOIN ticker t ON t.id = p.ticker_id
                JOIN date d ON p.date_id = d.id
            WHERE t.symbol = ?
            """,
            (symbol,),
        ).fetchone()[0]
        # Retrieve new OHLC data for symbol
        ohlc_data = tickers.tickers[symbol].history(start=latest_entry)[
            ["Open", "High", "Low", "Close", "Volume"]
        ]
        # Convert the date to a unix timestamp (remove timezone holding local time representations)
        ohlc_data.index = ohlc_data.index.tz_localize(None).astype("int") / 10**9
        ohlc_data.reset_index(inplace=True)
        # Convert to a list of dictionaries (records)
        ohlc_data = ohlc_data.to_dict(orient="records")
        with con:
            # Inserting date could be optimized
            con.executemany(
                """
                INSERT
                    OR IGNORE INTO date (date)
                VALUES (:Date)
                """,
                ohlc_data,
            )

            # Using an f-string is an SQL injection vulnerability,
            # but given the context it doesn't matter
            con.executemany(
                f"""
                INSERT INTO price (
                        ticker_id,
                        date_id,
                        OPEN,
                        high,
                        low,
                        close,
                        volume
                    )
                VALUES (
                        (
                            SELECT id
                            FROM ticker
                            WHERE symbol = '{symbol}'
                        ),
                        (
                            SELECT id
                            FROM date
                            WHERE date = :Date
                        ),
                        :Open,
                        :High,
                        :Low,
                        :Close,
                        :Volume
                    )
                """,
                ohlc_data,
            )
            print(f"Successfully updated {symbol}")
    except Exception as e:
        print(f"[{symbol}] {e}")
        # pass

# con.commit()
# con.close()
