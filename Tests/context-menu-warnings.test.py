#!/usr/bin/env python3
"""Bounded production context-menu lint and sandboxed offscreen behavior."""

import argparse
from collections import Counter
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    load("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs/Widgets/NContextMenu.qml"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("CONTEXT_MENU_LINT_COUNTS", dict(counts))
    assert not counts, dict(counts)
    assert result.returncode == 0, result.returncode


def stage_runtime(directory):
    load("simple-widgets-warnings").stage_runtime(directory)
    (directory / "tst_simple_widgets.qml").unlink()
    widgets = directory / "qs/Widgets"
    for name in ("NContextMenu", "NListView"):
        shutil.copyfile(ROOT / f"Widgets/{name}.qml", widgets / f"{name}.qml")
        with (widgets / "qmldir").open("a") as file:
            file.write(f"{name} 1.0 {name}.qml\n")
    style = directory / "qs/Commons/Style.qml"
    style.write_text(
        style.read_text().replace("QtObject {", "QtObject {\nproperty real radiusM: 8")
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/ContextMenuWarningsHarness.qml",
        directory / "tst_context_menu.qml",
    )


def runtime(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    stage_runtime(directory)
    # Hide both the config link and its Syncthing destination. All other host
    # paths are read-only; only this unique fixture directory is writable.
    command = [
        "bwrap",
        "--die-with-parent",
        "--unshare-net",
        "--ro-bind",
        "/",
        "/",
        "--bind",
        str(directory),
        str(directory),
        "--tmpfs",
        str(Path.home() / ".config"),
        "--tmpfs",
        str(settings.resolve().parent),
        "--",
        "/usr/lib/qt6/bin/qmltestrunner",
        "-input",
        str(directory / "tst_context_menu.qml"),
        "-import",
        str(directory),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=load("media-mini-warnings").isolate_environment(directory),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, result.returncode
        assert "0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
        ), output
    finally:
        assert settings.read_bytes() == original, "real settings changed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-context-menu-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        {"lint": lint, "runtime": runtime}[args.mode](directory)
