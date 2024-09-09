import numpy as np

np.float_ = np.float64

import logging

import pandas as pd
from loguru import logger
from prophet import Prophet
from tqdm import tqdm

from innov8.db_ops import data


def main() -> None:
    Prophet().fit(pd.DataFrame({"ds": ["2022-01-01", "2022-01-02"], "y": [0, 1]}))
    # Suppress logging from cmdstanpy
    logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

    symbols = data.main_table.symbol.unique()
    logger.info("Updating all...")
    for symbol in tqdm(symbols):
        data.add_new_ohlc(symbol)
    data.load_main_table(force_update=True)
    # Create an empty signal file to notify the main process of the update
    open(data.script_directory / "update_signal", "w").close()

    logger.info("Training models and generating forecasts...")
    data.clear_forecasts()
    for symbol in tqdm(symbols):
        data.generate_forecast(symbol)


if __name__ == "__main__":
    main()
