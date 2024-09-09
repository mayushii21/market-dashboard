import numpy as np

np.float_ = np.float64

import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import cast

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup, Tag
from loguru import logger
from prophet import Prophet
from tqdm import tqdm

# Fit a model to trigger cmdstanpy before setting logging level
Prophet().fit(pd.DataFrame({"ds": ["2022-01-01", "2022-01-02"], "y": [0, 1]}))
# Suppress logging from cmdstanpy
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)


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

    def __init__(self, script_directory: Path):
        self.script_directory = script_directory
        # Construct the absolute path to the database file
        db_path = script_directory / "stonks.db"
        # Connect to the database using the absolute path
        self.con = sqlite3.connect(db_path, check_same_thread=False)
        self.cur = self.con.cursor()
        self.ticker_symbols = None
        self.main_table: pd.DataFrame = None

        # Check if the database is populated by checking if the price table is present
        if not self.cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE TYPE = 'table'
                AND name = 'price'
            """
        ).fetchone():
            # Create necessary tables
            self.create_tables()
            self.initiate_tickers_obj(scrape=True)
            # Fill database with ticker information
            self.insert_ticker_info()
            # Download data and fill date and price tables
            self.fill_ohlc()
        # If the database is already populated
        else:
            self.initiate_tickers_obj(scrape=False)

        self.load_main_table()

    # Define function to scrape ticker symbols of S&P500 stocks
    @staticmethod
    def scrape_symbols():
        # Set the User-Agent header to a string that mimics a popular web browser to get past firewall rules
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        # Request and parse the web page
        r = requests.get(
            "https://www.slickcharts.com/sp500", headers=headers, timeout=120
        )
        soup = BeautifulSoup(r.text, "lxml")
        try:
            # Extract the text (replacing . with -) from the third cell (Symbol column) of each row of the main table
            # (ordered by component weights)
            return [
                tr.find_all("td")[2].text.replace(".", "-")
                for tr in cast(Tag, soup.find("tbody")).find_all("tr")
            ]
        except:
            with open(
                Path(__file__).resolve().parent / "sp500_tickers.txt", "r"
            ) as file:
                return [line.strip() for line in file]

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
        CREATE TABLE IF NOT EXISTS forecast (
            ticker_id INTEGER NOT NULL,
            date INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            PRIMARY KEY (ticker_id, date),
            FOREIGN KEY(ticker_id) REFERENCES ticker(id)
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
        DROP TABLE IF EXISTS forecast;
        """
        self.cur.executescript(drop_tables)
        self.cur.executescript(create_tables_query)
        self.con.commit()

    def insert_ticker_info(self):
        logger.info("Populating database with main ticker information...")
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
                    logger.debug("Successfully inserted info for {}", symbol)
            except Exception:
                logger.error("Failed to insert {}", symbol)

    def fill_ohlc(self):
        logger.info("Populating database with OHLC data...")
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
                    logger.debug("Successfully inserted OHLC data for {}", symbol[0])
            except Exception as e:
                logger.error("[{}] Exception: {}", symbol[0], e)

    def generate_forecast(self, symbol: str) -> None:
        df = self.main_table

        predictions = {}
        periods = 5
        for price_type in ["open", "high", "low", "close"]:
            # Prepare the dataframe for Prophet
            df_prophet = df.loc[df["symbol"] == symbol, ["date", price_type]].rename(
                columns={"date": "ds", price_type: "y"}
            )

            # Initialize and fit the Prophet model
            model = Prophet()
            model.fit(df_prophet)

            # Create a dataframe for future dates
            future = model.make_future_dataframe(
                periods=periods, freq="B"
            )  # 'B' is for business days
            forecast = model.predict(future)

            # Get the last period values
            last_period = df_prophet.diff().abs()["y"].tail(periods).to_numpy()
            last_price = df_prophet.iat[-1, 1]
            # Calculate the sum of the price differences (to be used in the margin)
            s = last_period.sum()
            # Resize the array to fit the predicted number of periods
            price_diffs = np.resize(last_period, periods * 2)

            forecasts = forecast[["ds", "yhat"]].tail(periods)
            for i in range(periods):
                # Calculate moving average
                margin = s / periods
                # Clip the price to be within the margin
                price = forecasts.iat[i, 1].clip(
                    last_price - margin, last_price + margin
                )
                # Add the new price difference
                price_diffs[i + periods] = abs(price - last_price)
                last_price = price
                # Update the sum
                s = s - price_diffs[i] + price_diffs[i + periods]
                forecasts.iat[i, 1] = price
            predictions[price_type] = forecasts

        # Store relevant data in the database
        for i in range(periods):
            d = predictions["open"].iloc[i]["ds"].tz_localize(None).timestamp()
            o = predictions["open"].iloc[i]["yhat"]
            c = predictions["close"].iloc[i]["yhat"]
            h = max(
                predictions["high"].iloc[i]["yhat"],
                o,
                c,
                predictions["low"].iloc[i]["yhat"],
            )
            l = min(
                predictions["low"].iloc[i]["yhat"],
                o,
                c,
                predictions["high"].iloc[i]["yhat"],
            )

            # Insert data into the database
            try:
                with self.con:
                    self.con.execute(
                        """
                        INSERT INTO forecast (ticker_id, date, open, high, low, close)
                        VALUES (
                            (
                                SELECT id
                                FROM ticker
                                WHERE symbol = ?
                            ),
                            ?, ?, ?, ?, ?
                        )
                        """,
                        (
                            symbol,
                            d,
                            o,
                            h,
                            l,
                            c,
                        ),
                    )
            except Exception as e:
                logger.error("[{}] Exception: {}", symbol, e)

    def clear_forecasts(self):
        with self.con:
            self.con.execute(
                """
                DELETE
                FROM forecast;
                """
            )

    def get_forecasts(self, symbol: str, date: datetime):
        with self.con:
            return self.con.execute(
                """
                SELECT open, high, low, close, date
                FROM forecast
                WHERE ticker_id = (
                    SELECT id
                    FROM ticker
                    WHERE symbol = ?
                )
                AND date >= ?
                ORDER BY date ASC
                LIMIT 1
                """,
                (symbol, date),
            ).fetchone()

    # Create DataFrame from SQL query
    def load_main_table(self, force_update=True):
        if (
            (update_signal := os.path.exists(self.script_directory / "update_signal"))
            or force_update
            or self.main_table is None
        ):
            logger.info("Loading main table...")
            if update_signal:
                os.remove(self.script_directory / "update_signal")
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
        logger.debug("Updating {}...", symbol)
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
            ohlc_data.index = ohlc_data.index.tz_localize(None).astype("int64") / 10**9
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
                logger.debug("{} updated \u2713", symbol)
        except Exception as e:
            logger.error("[{}] Exception: {}", symbol, e)


# Get the absolute path of the directory containing the script
script_directory = Path(__file__).resolve().parent

data = DataStore(script_directory)
