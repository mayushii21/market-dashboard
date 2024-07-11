import argparse
import os
import sys

from dotenv import load_dotenv
from loguru import logger

from innov8 import update_all
from innov8.layout import app

load_dotenv(".safe_env")
# Create server for gunicorn
server = app.server


def cli() -> None:
    parser = argparse.ArgumentParser(description="Innov8 Application CLI")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "update"],
        help='Run the main application (default) or update all tickers with "update"',
    )

    args = parser.parse_args()

    if args.command == "update":
        update_all.main()
    elif args.command == "run":
        main()
    else:
        parser.print_help()


def main() -> None:
    if os.getenv("DEV_ENV"):
        logger.configure(handlers=[{"sink": sys.stderr, "level": "DEBUG"}])
        app.run(debug=True, threaded=True)
    else:
        logger.configure(handlers=[{"sink": sys.stderr, "level": "ERROR"}])
        app.run(debug=False, threaded=True)


if __name__ == "__main__":
    main()
