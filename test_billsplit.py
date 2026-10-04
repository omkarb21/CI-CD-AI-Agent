from billsplit import add_tip, format_cents, parse_amount, split_evenly


def test_parse_amount():
    assert parse_amount("$12.50") == 1250


def test_add_tip():
    assert add_tip(1000, 18) == 1180


def test_format_cents():
    assert format_cents(123450) == "$1,234.50"


def test_split_evenly_with_leftover():
    assert split_evenly(10, 3) == [4, 3, 3]


def test_split_100_between_4():
    # Intentionally wrong: 100 split 4 ways is 25 each, not 30.
    assert split_evenly(100, 4) == [30, 30, 30, 30]
