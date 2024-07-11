from loguru import logger
from tqdm import tqdm

from innov8.db_ops import data


def main() -> None:
    logger.info("Updating all...")
    for symbol in tqdm(data.main_table.symbol.unique()):
        data.add_new_ohlc(symbol)


if __name__ == "__main__":
    main()
