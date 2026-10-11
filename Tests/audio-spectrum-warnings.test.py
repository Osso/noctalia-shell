#!/usr/bin/env python3
"""Standalone per-spectrum lint and isolated production-QML raster/geometry proof."""

import argparse
from collections import Counter
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("NMirroredSpectrum", "NLinearSpectrum", "NWaveSpectrum")


def load_helper():
    spec = importlib.util.spec_from_file_location(
        "workspace_runtime", ROOT / "Tests/workspace-runtime.test.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def stage(directory):
    helper = load_helper()
    helper.write_module(
        directory,
        "qs.Widgets.AudioSpectrum",
        {
            name: (ROOT / f"Widgets/AudioSpectrum/{name}.qml").read_text()
            for name in NAMES
        },
    )
    helper.write_module(
        directory,
        "qs.Commons",
        {
            "NColor": helper.singleton(
                'property color mPrimary: "white"\nproperty color mOnSurface: "white"'
            ),
            "Settings": helper.singleton(
                'property var data: ({audio: {visualizerType: "high"}, general: {animationDisabled: true}})'
            ),
        },
    )
    helper.write_module(
        directory,
        "qs.Services.Media",
        {
            "CavaService": helper.singleton("property var values: []"),
        },
    )
    (directory / "tst_audio_spectrum.qml").write_text(
        (ROOT / "Tests/Qml/AudioSpectrumHarness.qml").read_text()
    )


def lint(directory):
    failures = []
    for name in NAMES:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / f"qs/Widgets/AudioSpectrum/{name}.qml"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        (directory / f"{name}.lint.log").write_text(output)
        print(output, end="")
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
        print(name, "LINT_COUNTS", dict(counts), "EXIT", result.returncode)
        if warnings or result.returncode:
            failures.append(name)
    assert not failures, failures


def behavior(directory):
    environment = os.environ.copy()
    for key in (
        "WAYLAND_DISPLAY",
        "DISPLAY",
        "DBUS_SESSION_BUS_ADDRESS",
        "DBUS_SYSTEM_BUS_ADDRESS",
        "QML_IMPORT_PATH",
        "QML2_IMPORT_PATH",
    ):
        environment.pop(key, None)
    for key, folder in (
        ("HOME", "home"),
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_CACHE_HOME", "cache"),
        ("XDG_DATA_HOME", "data"),
        ("XDG_RUNTIME_DIR", "runtime"),
        ("NOCTALIA_CONFIG_DIR", "noctalia"),
    ):
        path = directory / folder
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        QSG_RHI_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent-spectrum-session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent-spectrum-system",
    )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory),
            "-import",
            str(directory),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "behavior.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0, result.returncode
    assert "0 failed" in output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    if args.artifacts:
        args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
        directory = args.artifacts
    else:
        temporary = tempfile.TemporaryDirectory(prefix="noctalia-spectrum-")
        directory = Path(temporary.name)
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    try:
        stage(directory)
        (lint if args.mode == "lint" else behavior)(directory)
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        assert backup.read_bytes() == original, "backup changed"
        print("SETTINGS_SHA_UNCHANGED", digest)


if __name__ == "__main__":
    main()
