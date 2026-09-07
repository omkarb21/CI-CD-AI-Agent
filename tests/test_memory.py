from db.memory import compute_error_signature


def test_signature_ignores_line_numbers_and_whitespace():
    a = "FAILED tests/test_foo.py:42 - AssertionError at line 42"
    b = "FAILED   tests/test_foo.py:99 - AssertionError at line 99"
    assert compute_error_signature(a) == compute_error_signature(b)


def test_signature_differs_for_different_errors():
    a = "AssertionError: expected 1 got 2"
    b = "TypeError: unsupported operand type"
    assert compute_error_signature(a) != compute_error_signature(b)
