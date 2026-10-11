"""Run qmllint on a staged behavior harness without hiding diagnostics."""

from pathlib import Path
import subprocess
import sys


def check_harness(module_root, harness):
    result = subprocess.run(
        ["/usr/lib/qt6/bin/qmllint", "-I", str(module_root), str(harness)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=60,
    )
    print(result.stdout, end="", file=sys.stdout)
    print(result.stderr, end="", file=sys.stderr)
    warnings = any(
        line.startswith("Warning:")
        for line in (result.stdout + result.stderr).splitlines()
    )
    return result.returncode or int(warnings)
