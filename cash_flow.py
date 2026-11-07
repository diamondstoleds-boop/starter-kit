"""Read the company cash flow file and return the latest month's figures."""

import csv
from datetime import datetime
from pathlib import Path

NUMBER_COLUMNS = ("cash_in", "cash_out", "net_cash_flow", "ending_balance")


class CashFlowError(Exception):
    """The file cannot be used. The message is safe to show in a report."""


def _read_row(row: dict) -> dict:
    try:
        datetime.strptime(row["month"], "%Y-%m")
        return {"month": row["month"], **{name: int(row[name]) for name in NUMBER_COLUMNS}}
    except (TypeError, ValueError):
        raise CashFlowError("invalid data in cash flow file") from None


def summarize_cash_flow(path: Path) -> dict:
    """Return the latest month's figures, plus a warning if its net looks wrong."""
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            missing = [
                name for name in ("month", *NUMBER_COLUMNS)
                if name not in (reader.fieldnames or [])
            ]
            if missing:
                raise CashFlowError("cash flow file is missing a column")
            rows = [_read_row(row) for row in reader]
    except OSError:
        raise CashFlowError("cash flow file could not be read") from None

    if not rows:
        raise CashFlowError("cash flow file has no rows")

    latest = max(rows, key=lambda row: row["month"])
    warnings = []
    if latest["net_cash_flow"] != latest["cash_in"] - latest["cash_out"]:
        warnings.append(
            f"Net cash flow for {latest['month']} does not equal cash in minus cash out."
        )
    return {**latest, "warnings": warnings}
