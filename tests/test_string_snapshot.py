from src.utils.string_snapshot import (
    truncate_for_display,
    truncate_params_string,
    truncate_single_string,
    truncate_string,
)


def test_truncate():
    string_short = "123456789"
    string_long = "123456789" * 15
    for f in (truncate_for_display, truncate_params_string, truncate_single_string):
        assert f(string_short) == string_short
        truncate = f(string_long)
        assert truncate.endswith("...")

    suffix_long = "......."

    assert truncate_string("123123", 5, suffix_long) == suffix_long
