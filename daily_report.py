"""Build the daily Markdown report, save it, and log the run.

Run:
    python3 daily_report.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from cash_flow import CashFlowError, summarize_cash_flow
from fetch_daily_prices import DATA_DIR, ENV_PATH, FetchError, fetch_daily_prices, get_api_key
from price_summary import PriceDataError, summarize_prices

BASE_DIR = Path(__file__).resolve().parent
WIB = ZoneInfo("Asia/Jakarta")
TICKERS = ("BBCA", "BBRI", "BMRI", "NISP")


def _rupiah(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}Rp {abs(amount):,}"


def _change(fraction) -> str:
    return "not available" if fraction is None else f"{fraction:+.2%}"


def _price_section(banks: list) -> list:
    if not banks:
        return ["## Bank prices", "No bank prices available."]
    lines = [
        "## Bank prices",
        "| Ticker | Last close (Rp) | Close date | Daily change | 30-day high (Rp) | 30-day low (Rp) | Volume |",
        "|---|---|---|---|---|---|---|",
    ]
    for bank in banks:
        lines.append(
            f"| {bank['ticker']} | {bank['last_close']:,} | {bank['close_date']} "
            f"| {_change(bank['daily_change'])} | {bank['high_30d']:,} "
            f"| {bank['low_30d']:,} | {bank['volume']:,} |"
        )
    return lines


def _cash_section(cash, cash_error) -> list:
    if cash is None:
        return ["## Company cash flow", f"Not available: {cash_error}"]
    lines = [
        f"## Company cash flow (through {cash['month']})",
        f"- Cash in: {_rupiah(cash['cash_in'])}",
        f"- Cash out: {_rupiah(cash['cash_out'])}",
        f"- Net cash flow: {_rupiah(cash['net_cash_flow'])}",
        f"- Ending balance: {_rupiah(cash['ending_balance'])}",
    ]
    lines += [f"- Warning: {warning}" for warning in cash["warnings"]]
    return lines


def render_report(when: datetime, banks: list, not_included: dict, cash, cash_error) -> str:
    """Return the report text. `when` must already be in WIB."""
    missing = [f"- {ticker}: {reason}" for ticker, reason in not_included.items()]
    sections = [
        [f"# Daily Report: {when:%Y-%m-%d} ({when:%H:%M} WIB)"],
        _price_section(banks),
        _cash_section(cash, cash_error),
        ["## Not included", *(missing or ["None"])],
    ]
    return "\n\n".join("\n".join(section) for section in sections) + "\n"


def _summarize_banks(api_key, key_error, data_dir: Path) -> tuple:
    """Return summaries for the banks that worked, and a reason for each that did not."""
    banks, not_included = [], {}
    for ticker in TICKERS:
        try:
            if key_error:
                raise FetchError(key_error)
            banks.append(summarize_prices(ticker, fetch_daily_prices(ticker, api_key, data_dir)))
        except FetchError as error:
            not_included[ticker] = f"price request failed ({error})"
        except PriceDataError as error:
            not_included[ticker] = str(error)
        except Exception as error:  # One bank's problem must not stop the others.
            not_included[ticker] = f"unexpected error ({type(error).__name__})"
    return banks, not_included


def run_daily_report(
    now=None,
    reports_dir: Path = BASE_DIR / "reports",
    log_path: Path = BASE_DIR / "logs" / "daily_report.log",
    data_dir: Path = DATA_DIR,
    cash_flow_path: Path = DATA_DIR / "cash_flow_sample.csv",
    env_path: Path = ENV_PATH,
    environ=os.environ,
) -> int:
    """Do one full run. Return 0 if at least one bank was reported, otherwise 1."""
    when = (now or datetime.now(WIB)).astimezone(WIB)

    api_key, key_error = None, None
    try:
        api_key = get_api_key(env_path, environ)
    except FetchError as error:
        key_error = str(error)
    banks, not_included = _summarize_banks(api_key, key_error, data_dir)

    cash, cash_error = None, None
    try:
        cash = summarize_cash_flow(cash_flow_path)
    except CashFlowError as error:
        cash_error = str(error)

    report_name = f"{when:%Y-%m-%d}.md"
    report_label = f"{reports_dir.name}/{report_name}"
    saved = True
    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / report_name).write_text(
            render_report(when, banks, not_included, cash, cash_error), encoding="utf-8"
        )
    except OSError:
        saved = False
        report_label = "not_saved"

    if not banks or not saved:
        status = "failed"
    elif not_included or cash is None:
        status = "partial"
    else:
        status = "ok"

    included_text = ",".join(bank["ticker"] for bank in banks) or "none"
    line = (
        f"{when.isoformat(timespec='seconds')} status={status} included={included_text} "
        f"not_included={','.join(not_included) or 'none'} "
        f"cash_flow={'ok' if cash else 'missing'} report={report_label}"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(line + "\n")
    print(line)
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    sys.exit(run_daily_report())
