#!/usr/bin/env python3
import ast
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


def load_safe_get_time():
    source_path = Path(__file__).resolve().parents[1] / "Bin" / "calendar-events.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    function_node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "safe_get_time")
    module = ast.Module(body=[function_node], type_ignores=[])
    ast.fix_missing_locations(module)

    namespace = {
        "datetime": datetime,
        "timezone": timezone,
        "time": time,
        "ICalGLib": SimpleNamespace(
            Timezone=SimpleNamespace(get_utc_timezone=lambda: "UTC"),
        ),
    }
    exec(compile(module, str(source_path), "exec"), namespace)
    return namespace["safe_get_time"]


class FakeICalTime:
    def __init__(
        self,
        *,
        year=2026,
        month=6,
        day=16,
        hour=12,
        minute=30,
        second=5,
        is_date=False,
        is_utc=True,
        converted=None,
        raises=False,
    ):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        self.date_only = is_date
        self.utc = is_utc
        self.converted = converted
        self.raises = raises
        self.convert_to_zone_calls = []

    def is_utc(self):
        return self.utc

    def convert_to_zone(self, zone):
        self.convert_to_zone_calls.append(zone)
        return self.converted or self

    def get_year(self):
        if self.raises:
            raise RuntimeError("bad calendar time")
        return self.year

    def get_month(self):
        return self.month

    def get_day(self):
        return self.day

    def is_date(self):
        return self.date_only

    def get_hour(self):
        return self.hour

    def get_minute(self):
        return self.minute

    def get_second(self):
        return self.second


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def test_safe_get_time():
    safe_get_time = load_safe_get_time()

    assert_equal(safe_get_time(None), None, "missing calendar time must return None")

    date_time = FakeICalTime()
    expected_timestamp = int(datetime(2026, 6, 16, 12, 30, 5, tzinfo=timezone.utc).timestamp())
    assert_equal(safe_get_time(date_time), expected_timestamp, "UTC date-time must become a Unix timestamp")

    date_only = FakeICalTime(year=2026, month=6, day=16, is_date=True)
    expected_date_timestamp = int(time.mktime(time.struct_time((2026, 6, 16, 0, 0, 0, 0, 0, -1))))
    assert_equal(safe_get_time(date_only), expected_date_timestamp, "date-only values must use local midnight")

    converted = FakeICalTime(hour=20, minute=15, second=0, is_utc=True)
    non_utc = FakeICalTime(is_utc=False, converted=converted)
    expected_converted_timestamp = int(datetime(2026, 6, 16, 20, 15, 0, tzinfo=timezone.utc).timestamp())
    assert_equal(safe_get_time(non_utc), expected_converted_timestamp, "non-UTC values must convert before timestamping")
    assert_equal(non_utc.convert_to_zone_calls, ["UTC"], "non-UTC values must request UTC conversion")

    assert_equal(safe_get_time(FakeICalTime(year=1969)), None, "years before Unix epoch must be rejected")
    assert_equal(safe_get_time(FakeICalTime(month=13)), None, "invalid months must be rejected")
    assert_equal(safe_get_time(FakeICalTime(day=32)), None, "invalid days must be rejected")
    assert_equal(safe_get_time(FakeICalTime(raises=True)), None, "calendar exceptions must fail closed")


if __name__ == "__main__":
    test_safe_get_time()
    print("ok test_safe_get_time")
