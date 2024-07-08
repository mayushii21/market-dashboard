import os
import sys

from dotenv import load_dotenv
from loguru import logger

from innov8.layout import app

load_dotenv(".safe_env")
# Create server for gunicorn
server = app.server


def main() -> None:
    if os.getenv("DEV_ENV"):
        logger.configure(handlers=[{"sink": sys.stderr, "level": "DEBUG"}])
        app.run(debug=True, threaded=True)
    else:
        logger.configure(handlers=[{"sink": sys.stderr, "level": "ERROR"}])
        app.run_server(debug=False, threaded=True)


if __name__ == "__main__":
    main()
