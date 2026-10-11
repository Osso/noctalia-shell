#!/usr/bin/env python3
"""Production NButton/NTextInput offscreen enabled-state and override proof.

Inert bootstrap services; no desktop surfaces or real settings persistence.
Lint retains the pre-existing unrelated owner/var warnings, never overrides.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("NButton", "NTextInput")


def load_helper(filename):
    spec = importlib.util.spec_from_file_location(
        "button_helper", ROOT / "Tests" / filename
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def behavior(directory):
    load_helper("clock-settings-warnings.test.py").stage_runtime(directory)
    (directory / "tst_clock.qml").unlink()
    harness = directory / "tst_buttons.qml"
    shutil.copyfile(ROOT / "Tests/Qml/ButtonEnabledWarningsHarness.qml", harness)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(harness),
            "-import",
            str(directory),
        ],
        cwd=directory,
        env=load_helper("datetime-tokens-layout-runtime.test.py").isolate_environment(
            directory
        ),
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "5 passed, 0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|qt\.qml\.|Warning:",
        output,
    ), output
    print("BUTTON_ENABLED_BEHAVIOR_PASS")


def lint(directory):
    load_helper("media-mini-warnings.test.py").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            *(str(directory / "qs/Widgets" / f"{name}.qml") for name in NAMES),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "lint.log").write_text(output)
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    # Qt emits the block-scope-var tag on a separate line.
    counts = Counter(
        re.findall(
            r"\[(property-override|unqualified|block-scope-var-declaration)\]", output
        )
    )
    assert counts == {"unqualified": 4, "block-scope-var-declaration": 2}, counts
    assert len(warnings) == 6 and result.returncode == 0, output
    print(
        "BUTTON_ENABLED_LINT_PASS: no override warnings; six unrelated baseline warnings retained"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = args.artifacts / "settings.backup.json"
    with backup.open("xb") as stream:
        os.chmod(backup, 0o600)
        stream.write(original)
    digest = hashlib.sha256(original).digest()
    assert backup.stat().st_mode & 0o777 == 0o600
    assert hashlib.sha256(backup.read_bytes()).digest() == digest
    try:
        (lint if args.mode == "lint" else behavior)(args.artifacts)
    finally:
        assert settings.read_bytes() == original, "Real settings changed"
        assert hashlib.sha256(backup.read_bytes()).digest() == digest, "Backup changed"
    print("Real settings and backup unchanged; bounded child exited.")


if __name__ == "__main__":
    main()
