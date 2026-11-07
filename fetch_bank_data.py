#!/usr/bin/env python3
"""Fetch full IDX company reports for selected banks into data/*.json."""

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://api.sectors.app/v2"
TICKERS = ("BBCA", "BBRI", "BMRI", "NISP")
PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"


def parse_env(contents):
    """Parse simple KEY=VALUE lines from a .env file."""
    values = {}
    for line in contents.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def read_api_key():
    """Read the API key from the environment or the project .env file."""
    key = os.environ.get("SECTORS_API_KEY", "").strip()
    env_file = PROJECT_DIR / ".env"
    if not key and env_file.is_file():
        key = parse_env(env_file.read_text(encoding="utf-8")).get("SECTORS_API_KEY", "").strip()
    if not key or key == "your-api-key-here":
        raise RuntimeError("SECTORS_API_KEY is missing. Set it in the project .env file.")
    return key


def output_path_for(ticker):
    if ticker not in TICKERS:
        raise ValueError(f"Unsupported ticker: {ticker}")
    return Path("data") / f"{ticker}.json"


def fetch_report(ticker, api_key):
    url = f"{BASE_URL}/company/report/{ticker}/"
    request = Request(url, headers={"Authorization": api_key, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code == 403:
            raise RuntimeError("Sectors API rejected the API key (HTTP 403). Check SECTORS_API_KEY.") from error
        if error.code == 404:
            raise RuntimeError(f"Sectors API report not found for {ticker} (HTTP 404).") from error
        raise RuntimeError(f"Sectors API request for {ticker} failed (HTTP {error.code}).") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach the Sectors API for {ticker}: {error.reason}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Sectors API returned invalid JSON for {ticker}.") from error


def main():
    try:
        api_key = read_api_key()
        print(api_key)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        for ticker in TICKERS:
            report = fetch_report(ticker, api_key)
            destination = PROJECT_DIR / output_path_for(ticker)
            destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Saved {ticker} report to {destination.relative_to(PROJECT_DIR)}")
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
