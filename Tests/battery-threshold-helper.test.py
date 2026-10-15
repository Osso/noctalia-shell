#!/usr/bin/python3
"""Behavioral tests for the fixed-target battery threshold helper."""

import contextlib
import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HELPER = Path(__file__).resolve().parents[1] / "Bin/noctalia-battery-threshold"
sys.dont_write_bytecode = True

INVALID_ARGUMENTS = (
    [],
    ["start"],
    ["start", "50", "extra"],
    ["START", "50"],
    ["other", "50"],
    ["../end", "50"],
    ["/tmp/threshold", "50"],
    ["start;touch /tmp/threshold", "50"],
    ["start", ""],
    ["start", "-1"],
    ["end", "101"],
    ["start", "+50"],
    ["start", " 50"],
    ["start", "50 "],
    ["start", "50\n"],
    ["start", "5.0"],
    ["start", "1e1"],
    ["start", "0x10"],
    ["start", "٥٠"],
    ["start", "５０"],
    ["start", "50; echo 100"],
    ["start", "50\n100"],
    ["start", "../50"],
    ["--directory=/tmp", "50"],
    ["start", "50", "--directory=/tmp"],
    ["start", "9" * 5000],
)


class BatteryThresholdHelperTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(HELPER.is_file(), "battery threshold helper is missing")
        loader = importlib.machinery.SourceFileLoader("battery_threshold", str(HELPER))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.helper = importlib.util.module_from_spec(spec)
        loader.exec_module(self.helper)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / "BAT0"
        self.directory.mkdir()
        self.start = self.directory / "charge_control_start_threshold"
        self.end = self.directory / "charge_control_end_threshold"
        self.start.write_text("20\n", encoding="ascii")
        self.end.write_text("80\n", encoding="ascii")

    def invoke(self, arguments):
        stderr = io.StringIO()
        stdout = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            result = self.helper.main(arguments, directory=self.directory)
        self.assertEqual(stdout.getvalue(), "")
        return result, stderr.getvalue()

    def test_writes_only_selected_threshold_with_newline(self):
        for threshold, value in (("start", "0"), ("start", "45"), ("end", "100")):
            with self.subTest(threshold=threshold, value=value):
                before = {path: path.read_bytes() for path in (self.start, self.end)}
                result, stderr = self.invoke([threshold, value])
                self.assertEqual(result, 0, stderr)
                self.assertEqual(stderr, "")
                selected = self.start if threshold == "start" else self.end
                other = self.end if threshold == "start" else self.start
                self.assertEqual(selected.read_bytes(), f"{value}\n".encode("ascii"))
                self.assertEqual(other.read_bytes(), before[other])

    def test_invalid_arguments_leave_all_files_unchanged(self):
        before = {path.name: path.read_bytes() for path in self.directory.iterdir()}
        for arguments in INVALID_ARGUMENTS:
            with self.subTest(arguments=repr(arguments)[:100]):
                result, stderr = self.invoke(arguments)
                self.assertNotEqual(result, 0)
                self.assertIn("noctalia-battery-threshold", stderr)
                self.assertEqual(
                    {path.name: path.read_bytes() for path in self.directory.iterdir()},
                    before,
                )

    def test_executable_rejects_invalid_arguments(self):
        self.assertTrue(os.access(HELPER, os.X_OK), "helper must be executable")
        for arguments in INVALID_ARGUMENTS:
            with self.subTest(arguments=repr(arguments)[:100]):
                result = subprocess.run(
                    [str(HELPER), *arguments],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("noctalia-battery-threshold", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_missing_threshold_is_not_created(self):
        self.start.unlink()
        result, stderr = self.invoke(["start", "30"])
        self.assertNotEqual(result, 0)
        self.assertIn(str(self.start), stderr)
        self.assertFalse(self.start.exists())
        self.assertEqual(self.end.read_bytes(), b"80\n")

    def test_open_failure_is_reported(self):
        self.end.unlink()
        self.end.mkdir()
        result, stderr = self.invoke(["end", "90"])
        self.assertNotEqual(result, 0)
        self.assertIn(str(self.end), stderr)
        self.assertEqual(self.start.read_bytes(), b"20\n")

    def test_write_failure_is_reported(self):
        self.start.unlink()
        self.start.symlink_to("/dev/full")
        result, stderr = self.invoke(["start", "30"])
        self.assertNotEqual(result, 0)
        self.assertIn(str(self.start), stderr)
        self.assertEqual(self.end.read_bytes(), b"80\n")


if __name__ == "__main__":
    unittest.main()
