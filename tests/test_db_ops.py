from pathlib import Path

import pytest
import yfinance as yf

from innov8.db_ops import DataStore

# Get the absolute path of the directory containing the script
script_directory = Path(__file__).resolve().parent
# Construct the absolute path to the database file
database_path = script_directory / "stonks.db"


@pytest.fixture(scope="module")
def data_store() -> DataStore:
    # Create a DataStore instance for testing
    data = DataStore(script_directory)
    data.create_tables()
    return data


def test_scrape_symbols(data_store):
    ticker_symbols = data_store.scrape_symbols()
    assert isinstance(ticker_symbols, list)
    assert len(ticker_symbols) > 300


def test_create_tables(data_store):
    # Test if the tables are created successfully in the test database
    data_store.cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = data_store.cur.fetchall()
    assert tables == [
        ("exchange",),
        ("ticker_type",),
        ("sector",),
        ("currency",),
        ("ticker",),
        ("date",),
        ("price",),
        ("forecast",),
    ]


def test_insert_ticker_info(data_store):
    # Mock the ticker_symbols attribute to avoid actual web scraping
    data_store.ticker_symbols = ["AAPL", "GOOGL"]
    # Initiate tickers instance
    data_store.tickers = yf.Tickers(" ".join(data_store.ticker_symbols))

    # Execute insertion
    data_store.insert_ticker_info()

    # Check if the ticker information is inserted into the database
    data_store.cur.execute("SELECT COUNT(*) FROM ticker")
    count = data_store.cur.fetchone()[0]
    assert count == len(data_store.ticker_symbols)


def test_fill_ohlc(data_store):
    # Fill test db
    data_store.fill_ohlc()

    # Check if the OHLC data is inserted into the database
    data_store.cur.execute("SELECT COUNT(*) FROM date")
    date_count = data_store.cur.fetchone()[0]
    data_store.cur.execute("SELECT COUNT(*) FROM price")
    price_count = data_store.cur.fetchone()[0]
    assert date_count > 0
    assert price_count == date_count * len(data_store.ticker_symbols)


def test_load_main_table(data_store):
    data_store.load_main_table()

    # Check if the main table is loaded successfully
    assert data_store.main_table is not None


def test_add_new_ohlc(data_store):
    # Delete a few records to simulate old data
    data_store.cur.execute("""
        DELETE FROM price
        WHERE (ticker_id, date_id) IN (
            SELECT p.ticker_id, p.date_id
            FROM price p
            JOIN date d 
                ON p.date_id = d.id
            JOIN ticker t 
                ON p.ticker_id = t.id
            WHERE t.symbol = "AAPL"
            ORDER BY d.date DESC
            LIMIT 3
        );
    """)

    # Store old data count
    data_store.cur.execute("SELECT COUNT(*) FROM price")
    price_count_1 = data_store.cur.fetchone()[0]

    # Add new data
    data_store.add_new_ohlc("AAPL")

    # Check new data count
    data_store.cur.execute("SELECT COUNT(*) FROM price")
    price_count_2 = data_store.cur.fetchone()[0]

    # Check if new OHLC data is added to the database
    assert price_count_2 > price_count_1


# Ensure the test database is deleted after testing
@pytest.fixture(scope="session", autouse=True)
def test_db_cleanup():
    yield
    database_path.unlink(missing_ok=True)
