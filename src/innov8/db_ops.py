import sqlite3

import requests
import yfinance as yf
from bs4 import BeautifulSoup
from tqdm import tqdm

# Connect to database
con = sqlite3.connect("stonks.db", check_same_thread=False)
cur = con.cursor()

# Check if the database is populated by checking if the price table is present
if not cur.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE TYPE = 'table'
        AND name = 'price'
    """
).fetchone():
    # Define function to scrape ticker symbols of S&P500 stocks
    def scrape_symbols():
        # Set the User-Agent header to a string that mimics a popular web browser to get past firewall rules
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        # Request and parse the web page
        r = requests.get("https://www.slickcharts.com/sp500", headers=headers)
        soup = BeautifulSoup(r.text, "lxml")
        # Extract the text (replacing . with -) from the third cell (Symbol column) of each row of the main table
        # (ordered by component weights)
        return [
            tr.find_all("td")[2].text.replace(".", "-")
            for tr in soup.find("tbody").find_all("tr")
        ]

    def create_tables():
        create_tables_query = """
        CREATE TABLE IF NOT EXISTS exchange (
            id INTEGER PRIMARY KEY NOT NULL,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS ticker_type (
            id INTEGER PRIMARY KEY NOT NULL,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS sector (
            id INTEGER PRIMARY KEY NOT NULL,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS currency (
            id INTEGER PRIMARY KEY NOT NULL,
            iso_code TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS ticker (
            id INTEGER PRIMARY KEY NOT NULL,
            currency_id INTEGER NOT NULL,
            exchange_id INTEGER NOT NULL,
            ticker_type_id INTEGER NOT NULL,
            sector_id INTEGER NOT NULL,
            symbol TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            FOREIGN KEY(currency_id) REFERENCES currency(id),
            FOREIGN KEY(exchange_id) REFERENCES exchange(id),
            FOREIGN KEY(ticker_type_id) REFERENCES ticker_type(id),
            FOREIGN KEY(sector_id) REFERENCES sector(id)
        );
        CREATE TABLE IF NOT EXISTS date (
            id INTEGER PRIMARY KEY NOT NULL,
            date INTEGER NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS price (
            ticker_id INTEGER NOT NULL,
            date_id INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL,
            PRIMARY KEY (ticker_id, date_id),
            FOREIGN KEY(ticker_id) REFERENCES ticker(id),
            FOREIGN KEY(date_id) REFERENCES date(id)
        );
        CREATE INDEX IF NOT EXISTS fk_ticker_idx ON ticker (
            sector_id,
            exchange_id,
            currency_id,
            ticker_type_id
        );
        """
        drop_tables = """
        DROP TABLE IF EXISTS ticker;
        DROP TABLE IF EXISTS exchange;
        DROP TABLE IF EXISTS price;
        DROP TABLE IF EXISTS date;
        DROP TABLE IF EXISTS ticker_type;
        DROP TABLE IF EXISTS sector;
        DROP TABLE IF EXISTS currency;
        """
        cur.executescript(drop_tables)
        cur.executescript(create_tables_query)
        con.commit()

    def insert_ticker_info():
        print("Populating database with main ticker information...")
        for symbol in tqdm(ticker_symbols):
            try:
                with con:
                    info = tickers.tickers[symbol].info
                    con.execute(
                        """
                        INSERT
                            OR IGNORE INTO currency (iso_code)
                        VALUES (:currency)
                        """,
                        info,
                    )
                    con.execute(
                        """
                        INSERT
                            OR IGNORE INTO exchange (name)
                        VALUES (:exchange)
                        """,
                        info,
                    )
                    con.execute(
                        """
                        INSERT
                            OR IGNORE INTO ticker_type (name)
                        VALUES (:quoteType)
                        """,
                        info,
                    )
                    con.execute(
                        """
                        INSERT
                            OR IGNORE INTO sector (name)
                        VALUES (:sector)
                        """,
                        info,
                    )
                    con.execute(
                        """
                        INSERT INTO ticker (
                                name,
                                symbol,
                                currency_id,
                                exchange_id,
                                ticker_type_id,
                                sector_id
                            )
                        VALUES (
                                :shortName,
                                :symbol,
                                (
                                    SELECT id
                                    FROM currency
                                    WHERE iso_code = :currency
                                ),
                                (
                                    SELECT id
                                    FROM exchange
                                    WHERE name = :exchange
                                ),
                                (
                                    SELECT id
                                    FROM ticker_type
                                    WHERE name = :quoteType
                                ),
                                (
                                    SELECT id
                                    FROM sector
                                    WHERE name = :sector
                                )
                            )
                        """,
                        info,
                    )
                    # print(f"Successfully inserted info for {symbol}")
            except Exception:
                # print(f"Failed to insert {symbol}")
                pass

    def fill_ohlc():
        print("Populating database with OHLC data...")
        # Per ticker OHLC data retrieval - helps avoid rate limiting
        for symbol in tqdm(
            cur.execute(
                """
                SELECT symbol
                FROM ticker
                """
            ).fetchall()
        ):
            try:
                # Retrieve OHLC data for symbol
                ohlc_data = tickers.tickers[symbol[0]].history(
                    start="2022-07-01", end="2023-07-01"
                )[["Open", "High", "Low", "Close", "Volume"]]
                # Convert the date to a unix timestamp (remove timezone holding local time representations)
                ohlc_data.index = (
                    ohlc_data.index.tz_localize(None).astype("int") / 10**9
                )
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
                    # but given the context it doesn't matter, can be easily fixed if needed
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
                                    WHERE symbol = '{symbol[0]}'
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
                    # print(f"Successfully inserted OHLC data for {symbol[0]}")
            except Exception as e:
                # print(f"[{symbol[0]}] Exception: {e}")
                pass

    ticker_symbols = scrape_symbols()
    # Create necessary tables
    create_tables()
    # Initiate tickers instance
    tickers = yf.Tickers(" ".join(ticker_symbols))
    # Fill database with ticker information
    insert_ticker_info()
    # Download data and fill date and price tables
    fill_ohlc()
# If the database is already populated
else:
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
    tickers = yf.Tickers(" ".join(ticker_symbols))


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
        print(f"[{symbol}] Exception: {e}")
        # pass


print("Successfully established DB connection")

# con.commit()
# con.close()
# con.close()
