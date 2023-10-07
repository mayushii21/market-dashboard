import sqlite3
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from tqdm import tqdm


# Define class for data storage operations
class DataStore:
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

    def __init__(self, database_path):
        # Connect to the database using the absolute path
        self.con = sqlite3.connect(database_path, check_same_thread=False)
        self.cur = self.con.cursor()
        self.ticker_symbols = None
        self.main_table = None
        self.tickers = None

    # Define function to scrape ticker symbols of S&P500 stocks
    @staticmethod
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

    def create_tables(self):
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
        self.cur.executescript(drop_tables)
        self.cur.executescript(create_tables_query)
        self.con.commit()

    def insert_ticker_info(self):
        print("Populating database with main ticker information...")
        for symbol in tqdm(self.ticker_symbols):
            try:
                with self.con:
                    info = self.tickers.tickers[symbol].info
                    self.con.execute(
                        """
                        INSERT
                            OR IGNORE INTO currency (iso_code)
                        VALUES (:currency)
                        """,
                        info,
                    )
                    self.con.execute(
                        """
                        INSERT
                            OR IGNORE INTO exchange (name)
                        VALUES (:exchange)
                        """,
                        info,
                    )
                    self.con.execute(
                        """
                        INSERT
                            OR IGNORE INTO ticker_type (name)
                        VALUES (:quoteType)
                        """,
                        info,
                    )
                    self.con.execute(
                        """
                        INSERT
                            OR IGNORE INTO sector (name)
                        VALUES (:sector)
                        """,
                        info,
                    )
                    self.con.execute(
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

    def fill_ohlc(self):
        print("Populating database with OHLC data...")
        # Per ticker OHLC data retrieval - helps avoid rate limiting
        for symbol in tqdm(
            self.cur.execute(
                """
                SELECT symbol
                FROM ticker
                """
            ).fetchall()
        ):
            try:
                # Retrieve OHLC data for symbol
                ohlc_data = self.tickers.tickers[symbol[0]].history(
                    start="2022-07-01", end="2023-07-01"
                )[["Open", "High", "Low", "Close", "Volume"]]
                # Convert the date to a unix timestamp (remove timezone holding local time representations)
                ohlc_data.index = (
                    ohlc_data.index.tz_localize(None).astype("int64") / 10**9
                )
                ohlc_data.reset_index(inplace=True)
                # Convert to a list of dictionaries (records)
                ohlc_data = ohlc_data.to_dict(orient="records")
                with self.con:
                    # Inserting date could be optimized
                    self.con.executemany(
                        """
                        INSERT
                            OR IGNORE INTO date (date)
                        VALUES (:Date)
                        """,
                        ohlc_data,
                    )

                    # Using an f-string is an SQL injection vulnerability,
                    # but given the context it doesn't matter, can be easily fixed if needed
                    self.con.executemany(
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

    # Create DataFrame from SQL query
    def load_main_table(self):
        self.main_table = pd.read_sql_query(
            self.main_query,
            self.con,
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

    def initiate_tickers_obj(self, scrape):
        if scrape:
            self.ticker_symbols = self.scrape_symbols()
        else:
            self.ticker_symbols = [
                symbol[0]
                for symbol in self.con.execute(
                    """
                    SELECT symbol
                    FROM ticker
                    """
                ).fetchall()
            ]
        # Initiate tickers instance
        self.tickers = yf.Tickers(" ".join(self.ticker_symbols))

    # Define function for updating ohlc data for a given ticker by it's symbol
    def add_new_ohlc(self, symbol):
        try:
            # Get date for latest entry
            latest_entry = self.cur.execute(
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
            ohlc_data = self.tickers.tickers[symbol].history(
                start=latest_entry, raise_errors=True
            )[["Open", "High", "Low", "Close", "Volume"]]
            # Convert the date to a unix timestamp (remove timezone holding local time representations)
            ohlc_data.index = (
                ohlc_data.index.tz_localize(None).astype("int64") / 10**9
            )
            ohlc_data.reset_index(inplace=True)
            # Convert to a list of dictionaries (records)
            ohlc_data = ohlc_data.to_dict(orient="records")
            with self.con:
                # Inserting date could be optimized
                self.con.executemany(
                    """
                    INSERT
                        OR IGNORE INTO date (date)
                    VALUES (:Date)
                    """,
                    ohlc_data,
                )

                # Using an f-string is an SQL injection vulnerability,
                # but given the context it doesn't matter
                self.con.executemany(
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
                # print(f"Successfully updated {symbol}")
        except Exception as e:
            # print(f"[{symbol}] Exception: {e}")
            pass


# Get the absolute path of the directory containing the script
script_directory = Path(__file__).resolve().parent
# Construct the absolute path to the database file
database_path = script_directory / "stonks.db"
data = DataStore(database_path)

# Check if the database is populated by checking if the price table is present
if not data.cur.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE TYPE = 'table'
        AND name = 'price'
    """
).fetchone():
    # Create necessary tables
    data.create_tables()
    data.initiate_tickers_obj(scrape=True)
    # Fill database with ticker information
    data.insert_ticker_info()
    # Download data and fill date and price tables
    data.fill_ohlc()
# If the database is already populated
else:
    data.initiate_tickers_obj(scrape=False)

data.load_main_table()

# print("Successfully established DB connection")

# con.commit()
# con.close()
