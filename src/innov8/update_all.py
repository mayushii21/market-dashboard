import sys

import numpy as np

np.float_ = np.float64  # type: ignore

from loguru import logger
from tqdm import tqdm

from innov8.db_ops import data


def main() -> None:
    logger.configure(handlers=[{"sink": sys.stderr, "level": "INFO"}])

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
