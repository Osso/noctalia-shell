#!/usr/bin/env python3
"""Exact-file lint and offscreen production clipboard preview lifecycle.

Clipboard service is an inert cache/decode boundary, never the real clipboard.
Preview, formatter, rounded image, Qt controls and Loader remain production.
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
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Launcher/ClipboardPreview.qml")


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    load_helper("clipboard_lint_staging", "media-mini-warnings.test.py").stage_modules(
        directory
    )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    warnings = re.findall(r"^Warning:.*$", output, re.M)
    counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
    print("CLIPBOARD_PREVIEW_LINT_COUNTS", dict(counts))
    assert counts == {"missing-property": 1}, dict(counts)
    assert 'Member "mOutlineVariant" not found on type "NColor"' in output
    assert result.returncode == 0, result.returncode
    print("CLIPBOARD_PREVIEW_LINT_PASS")


def stage_runtime(directory):
    helpers = load_helper("clipboard_module_helpers", "file-picker-warnings.test.py")
    write = helpers.write_module
    singleton = helpers.singleton
    write(
        directory,
        "Quickshell",
        {"Quickshell": singleton(f'property string shellDir: "{directory}"')},
    )
    write(directory, "Quickshell.Widgets", {"Unused": "import QtQuick\nItem {}"})
    write(
        directory,
        "qs.Commons",
        {
            "Style": singleton("""property real marginL: 12
property real marginS: 4
property real radiusM: 8
property real radiusS: 4
property real baseWidgetSize: 32
property real fontSizeM: 12
property real fontSizeXXL: 24"""),
            "NColor": singleton(
                "\n".join(
                    f'property color {name}: "{color}"'
                    for name, color in {
                        "mSurface": "#202020",
                        "mSurfaceVariant": "#303030",
                        "mOutline": "#505050",
                        "mOutlineVariant": "#606060",
                        "mOnSurface": "white",
                        "transparent": "transparent",
                    }.items()
                )
            ),
        },
    )
    write(
        directory,
        "qs.Services.Keyboard",
        {
            "ClipboardService": singleton("""
property int revision: 0
property var imageDataById: ({})
property var callbacks: ({})
property string requestedImageId: ""
function getImageData(id) { return imageDataById[id]; }
function decode(id, callback) { callbacks[id] = callback; }
function decodeToDataUrl(id, mime, callback) { requestedImageId = id; }
function finishText(id, content) {
  const callback = callbacks[id];
  delete callbacks[id];
  callback(content);
}
function publishImage(id, url) {
  imageDataById[id] = url;
  revision++;
}
function reset() {
  imageDataById = ({});
  callbacks = ({});
  requestedImageId = "";
  revision = 0;
}
""")
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            "NImageRounded": (ROOT / "Widgets/NImageRounded.qml").read_text(),
            "NIcon": "import QtQuick\nItem { property string icon; property real pointSize }",
        },
    )
    write(
        directory,
        "qs.Modules.Panels.Launcher",
        {"ClipboardPreview": (ROOT / TARGET).read_text()},
    )
    helpers_path = directory / "qs/Helpers"
    helpers_path.mkdir()
    shutil.copyfile(
        ROOT / "Helpers/TextFormatter.js", helpers_path / "TextFormatter.js"
    )
    shutil.copytree(ROOT / "Shaders/qsb", directory / "Shaders/qsb")
    # Two concrete images, used both as data URLs and local file paths.
    image = directory / "red.svg"
    image.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="6"><rect width="8" height="6" fill="red"/></svg>'
    )
    source = (ROOT / "Tests/Qml/ClipboardPreviewWarningsHarness.qml").read_text()
    (directory / "tst_clipboard_preview.qml").write_text(
        source.replace("@IMAGE_PATH@", image.as_uri())
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
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
        and key
        not in {
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "HOME",
            "NIRI_SOCKET",
            "HYPRLAND_INSTANCE_SIGNATURE",
            "SWAYSOCK",
        }
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "NOCTALIA_CONFIG_DIR",
        "NOCTALIA_CACHE_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    stage_runtime(directory)
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_clipboard_preview.qml"),
                "-import",
                str(directory),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, result.returncode
        assert "0 failed" in output
        assert not re.search(r"QWARN|QFATAL|ReferenceError|TypeError", output), output
        print("CLIPBOARD_PREVIEW_RUNTIME_PASS")
    finally:
        assert settings.read_bytes() == original, "real settings changed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("lint", "runtime"), required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-clipboard-preview-") as temporary:
        {"lint": lint, "runtime": runtime}[args.mode](Path(temporary))
