<!-- better use an svg -->
<div align="center">
    <img src="doc/pixel_neko.png">
</div>

-------

# innov8finance: interactive market dashboard [![brought to you by bread cat](https://img.shields.io/badge/made_with_%F0%9F%8D%9E_by-(%E2%81%A0%5E%E2%81%A0.%E2%81%A0__%E2%81%A0.%E2%81%A0%5E%E2%81%A0)%E2%81%A0%EF%BE%89-966FD6?style=for-the-badge)](https://github.com/mayushii21)

<div align="center">

<!-- search for "github release" -->
![GitHub release (with filter)](https://img.shields.io/github/v/release/mayushii21/market-dashboard?style=flat-square)
![Static Badge](https://img.shields.io/badge/status-beta-yellow?style=flat-square)
[![black autoformatter](https://img.shields.io/badge/code_style-black-000000)](https://github.com/psf/black)
[![CodeFactor](https://www.codefactor.io/repository/github/mayushii21/market-dashboard/badge?style=flat-square)](https://www.codefactor.io/repository/github/mayushii21/market-dashboard)
[![License](https://img.shields.io/github/license/mayushii21/market-dashboard?style=flat-square)](LICENSE)

</div>

**innov8finance** is a versatile market dashboard designed to meet the needs of traders, offering an innovative alternative to Tradingview with a plethora of aesthetically pleasing themes to choose from. It provides users with the convenience of accessing the platform online or hosting it locally on their machine. This allows traders to have uninterrupted access to historical tick data even when the grid is down, ensuring they can backtest their trading strategies anytime, anywhere. Experience the power of innov8finance for reliable and efficient trading analysis.

> LEGAL DISCLAIMER  
This project is intended for research and educational purposes only. The Yahoo! finance API is intended for personal use only.

## Features

-
-
-

## Usage and Installation

**innov8finance** requires Python (>= 3.8), requests, beautifulsoup4, pandas, yfinance, dash and other dependencies. However...

## Development

**innov8finance** uses Dash and Plotly for the front end and Pandas and SQLite for the back end. Data is obtained from Yahoo! Finance's API and stored in an SQLite database. Necessary data is then queried and loaded into a Pandas DataFrame for further data manipulation. Interactive charts are plotted with Plotly and inserted into the Dash app's layout along with other components, creating a smooth dashboard experience.

The choice of database (SQLite) was mainly influenced by hosting platform limitations. Ideally, a timeseries DB such as TimeScaleDB (with a hypertable to store the tick data and the use of a time_bucket for interval aggregation) or a fast column-oriented DBMS such as Clickhouse would be used. Creating a materialized view paired with a trigger to refresh the materialized view [concurrently] could also greatly boost performance, if storage space limitations were not an issue.

Given the...
...the database is normalized to handle data anomalies and the following schema was decided on:

[pic]

Primary keys and attributes (columns) with unique constraints are automatically indexed, so they are left untouched. On the other hand, indexes on foreign keys are not automatically created, so a composite index is created on the foreign keys of the ticker table to speed up querying.

Order of composite indexes:

- ticker - (sector_id, exchange_id, currency_id, ticker_type_id)
- price - (ticker_id, date_id)  

*process*

<!-- add link to "archive" here -->
> Note: Early development of the MVP can be viewed in the Jupyter Notebooks in the archive folder.

#### Roadmap

- replace the Plotly candlestick chart with TradingView Lightweight Charts
- move indicators (with settings, as well as a color picker) to a single dropup element
- add VWAP, RSI, MACD, Parabolic SAR, ATR and other indicators
- migrate from SQLite to TimeScaleDB or Clickhouse
- switch from Pandas to Polars
- add support for multiple timeframes, as well as an interval selection button group
- optimize code with clientside callbacks using JS where possible
- add dbc.Progress to update button (instead of loading)
- add components as option labels for sector and symbol dropdowns (scrape and add svgs)
- add greyed out truncated names of tickers, as well as custom search terms for symbol dropdown

## License

[BSD 3-Clause License](LICENSE)  
Copyright (c) 2023, mayushii21

## Contact

Telegram: [@mayushii21](https://t.me/mayushii21)  
Email: <the.real.mayushii21@gmail.com>
