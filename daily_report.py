"""Build the daily Markdown report."""

from datetime import datetime


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
