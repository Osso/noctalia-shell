"""Run qmllint on a staged behavior harness without hiding diagnostics."""

from pathlib import Path
import subprocess
import sys


def check_harness(module_root, harness):
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "--bare",
            "-I",
            str(module_root),
            "-I",
            "/usr/lib/qt6/qml",
            "--max-warnings",
            "0",
            "--json",
            "-",
            str(harness),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=60,
    )
    print(result.stdout, file=sys.stdout)
    print(result.stderr, end="", file=sys.stderr)
    return result.returncode
