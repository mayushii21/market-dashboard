from loguru import logger
from tqdm import tqdm

from innov8.db_ops import data


def main() -> None:
    logger.info("Updating all...")
    for symbol in tqdm(data.main_table.symbol.unique()):
        data.add_new_ohlc(symbol)
    # Create an empty signal file to notify the main process of the update
    open(data.script_directory / "update_signal", "w").close()


if __name__ == "__main__":
    main()
