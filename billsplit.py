"""Small bill-splitting helpers. All money is handled in integer cents."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def _round_half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_amount(text: str) -> int:
    """Parse a string like '$12.50' or '1,234.5' into cents."""
    cleaned = text.strip().replace("$", "").replace(",", "")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"not a valid amount: {text!r}") from None
    if value < 0:
        raise ValueError("amount cannot be negative")
    return _round_half_up(value * 100)


def add_tip(cents: int, percent: float) -> int:
    """Return the total after adding a tip, rounded to the nearest cent."""
    tip = Decimal(cents) * Decimal(str(percent)) / 100
    return cents + _round_half_up(tip)


def split_evenly(cents: int, people: int) -> list[int]:
    """Split cents among people. Leftover cents go to the first few people."""
    if people <= 0:
        raise ValueError("people must be at least 1")
    base, remainder = divmod(cents, people)
    return [base + 1 if i < remainder else base for i in range(people)]


def format_cents(cents: int) -> str:
    """Format cents as a dollar string, e.g. 123450 -> '$1,234.50'."""
    return f"${cents // 100:,}.{cents % 100:02d}"
