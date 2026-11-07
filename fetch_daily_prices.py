"""Fetch recent daily prices from the Sectors API and save each ticker's file."""

import json
import os
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
DATA_DIR = BASE_DIR / "data"
TIMEOUT_SECONDS = 30


class FetchError(Exception):
    """A fetch failed. The message is safe to show in reports and logs."""


def get_api_key(env_path=ENV_PATH, environ=os.environ) -> str:
    """Return the key from the environment, or else from the .env file."""
    key = environ.get("SECTORS_API_KEY", "").strip()
    if not key and env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "SECTORS_API_KEY":
                key = value.strip().strip("\"'")
    if not key:
        raise FetchError("SECTORS_API_KEY is not set")
    return key


def fetch_daily_prices(ticker: str, api_key: str, data_dir: Path = DATA_DIR) -> list:
    """Fetch the last 30 days for a ticker, save them, and return the rows.

    A failure raises FetchError and leaves the last good file untouched. The
    original exception text is left out of the message on purpose, so nothing
    from the request can reach a report or log.
    """
    url = f"https://api.sectors.app/v2/daily/{ticker}/"
    try:
        response = requests.get(
            url, headers={"Authorization": api_key}, timeout=TIMEOUT_SECONDS
        )
    except requests.RequestException as error:
        raise FetchError(f"network error ({type(error).__name__})") from None

    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code}")
    try:
        rows = response.json()
    except ValueError:
        raise FetchError("unexpected response") from None
    if not isinstance(rows, list):
        raise FetchError("unexpected response")
    if not rows:
        raise FetchError("no price data returned")

    # Write to a temporary file first, so a crash cannot leave a half-written file.
    data_dir.mkdir(parents=True, exist_ok=True)
    temporary = data_dir / f".daily_{ticker}.json.tmp"
    temporary.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    temporary.replace(data_dir / f"daily_{ticker}.json")
    return rows
