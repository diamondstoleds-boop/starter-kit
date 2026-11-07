"""Turn a ticker's saved daily price rows into the figures the report shows."""

from datetime import date

NUMBER_FIELDS = ("close", "high", "low", "volume")


class PriceDataError(Exception):
    """The price rows cannot be trusted. The message is safe to show in a report."""


def _check_row(row) -> None:
    if not isinstance(row, dict):
        raise PriceDataError("invalid price data")
    try:
        date.fromisoformat(row["date"])
    except (KeyError, TypeError, ValueError):
        raise PriceDataError("invalid price data") from None
    for field in NUMBER_FIELDS:
        value = row.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise PriceDataError("invalid price data")


def summarize_prices(ticker: str, rows: list) -> dict:
    """Return the last close, its date, daily change, 30-day range and volume.

    daily_change is a fraction (0.0146 means +1.46%), or None when there is no
    earlier close to compare with.
    """
    if not rows:
        raise PriceDataError("no price data")
    for row in rows:
        _check_row(row)

    ordered = sorted(rows, key=lambda row: row["date"])
    latest = ordered[-1]
    previous_close = ordered[-2]["close"] if len(ordered) > 1 else None
    daily_change = None
    if previous_close:
        daily_change = (latest["close"] - previous_close) / previous_close

    return {
        "ticker": ticker,
        "last_close": latest["close"],
        "close_date": latest["date"],
        "daily_change": daily_change,
        "high_30d": max(row["high"] for row in ordered),
        "low_30d": min(row["low"] for row in ordered),
        "volume": latest["volume"],
    }
