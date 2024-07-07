import os

from dotenv import load_dotenv

from innov8.layout import app

load_dotenv(".safe_env")
# Create server for gunicorn
server = app.server


def main() -> None:
    if os.getenv("DEV_ENV"):
        app.run(debug=True, threaded=True)
    else:
        app.run_server(debug=False, threaded=True)


if __name__ == "__main__":
    main()
