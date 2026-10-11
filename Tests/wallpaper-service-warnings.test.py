#!/usr/bin/env python3
"""WallpaperService-only lint and isolated QML behavior; no desktop or real I/O.

RED controls mutate only the staged service. Lint uses real installed metadata,
never the runtime mocks. Runtime executes production service with inert process,
folder and persistence boundaries; it proves routing/state, not rendering or I/O.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = Path("Services/UI/WallpaperService.qml")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "--json",
            "-",
            "-I",
            str(directory),
            str(directory / "qs" / SERVICE),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        cwd=ROOT,
    )
    (directory / "lint.json").write_text(result.stdout)
    assert result.returncode == 0, result.stderr
    warnings = json.loads(result.stdout)["files"][0]["warnings"]
    counts = Counter(w["id"] for w in warnings if w["type"] == "warning")
    print("WALLPAPER_SERVICE_WARNINGS", dict(counts))
    # Only proven lexical owners are gated. Unbound component/type diagnostics
    # remain visible in full JSON, as do pre-existing hoisting diagnostics.
    owners = [
        w
        for w in warnings
        if w["id"] == "unqualified"
        and (
            not w.get("suggestions")
            or any(
                "scanningCount is a member" in s.get("message", "")
                for s in w.get("suggestions", [])
            )
        )
    ]
    assert not owners, [(w["line"], w["message"]) for w in owners]


def stage_runtime(directory, mutation):
    utility = helper("workspace-runtime")
    write = utility.write_module
    singleton = utility.singleton
    write(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nQtObject { default property list<QtObject> children }",
            "ShellScreen": "import QtQuick\nQtObject { property string name }",
            "Quickshell": singleton(
                'property string shellDir: "/fixture"\nproperty var screens: []'
            ),
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "FixtureIo": singleton(
                "property int writes: 0\nproperty var cache: null\nproperty var processes: []"
            ),
            "FileView": """import QtQuick
QtObject {
  id: view
  property string path
  property bool printErrors
  property bool watchChanges
  property QtObject adapter
  signal loaded()
  signal loadFailed(int error)
  function writeAdapter() { FixtureIo.writes++; }
  Component.onCompleted: FixtureIo.cache = view
}""",
            "JsonAdapter": "import QtQuick\nQtObject {}",
            "StdioCollector": 'import QtQuick\nQtObject { property string text: "" }',
            "Process": """import QtQuick
QtObject {
  id: process
  property var command: []
  property bool running: false
  property QtObject stdout
  property QtObject stderr
  signal exited(int exitCode, int exitStatus)
  function finish(code, text) { stdout.text = text; exited(code, 0); }
  Component.onCompleted: FixtureIo.processes = FixtureIo.processes.concat([process])
  Component.onDestruction: FixtureIo.processes = FixtureIo.processes.filter(p => p !== process)
}""",
        },
    )
    write(
        directory,
        "Qt.labs.folderlistmodel",
        {
            "FixtureFolders": singleton("property var scanners: []"),
            "FolderListModel": """import QtQuick
QtObject {
  id: scanner
  enum Status { Null, Loading, Ready }
  enum SortField { Name }
  property int status: FolderListModel.Null
  property string folder
  property var nameFilters
  property bool showDirs
  property int sortField
  property var files: []
  readonly property int count: files.length
  function get(index, role) { return files[index]; }
  Component.onCompleted: FixtureFolders.scanners = FixtureFolders.scanners.concat([scanner])
  Component.onDestruction: FixtureFolders.scanners = FixtureFolders.scanners.filter(s => s !== scanner)
}""",
        },
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())[
        "wallpaper"
    ]
    defaults.update(
        randomEnabled=False, recursiveSearch=False, directory="/fixture/images"
    )
    fields = []
    for key, value in defaults.items():
        kind = (
            "bool"
            if isinstance(value, bool)
            else "real"
            if isinstance(value, (int, float))
            else "var"
        )
        fields.append(f"property {kind} {key}: {json.dumps(value)}")
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                'property string cacheDir: "/fixture/"\nproperty QtObject data: QtObject { property QtObject wallpaper: QtObject {\n'
                + "\n".join(fields)
                + "\n} }\nfunction preprocessPath(path) { return path; }"
            ),
            "I18n": singleton(
                "property bool isLoaded: true\nfunction tr(key) { return key; }"
            ),
            "Logger": singleton(
                "function d(...args) {}\nfunction i(...args) {}\nfunction w(...args) {}"
            ),
        },
    )
    source = (ROOT / SERVICE).read_text()
    if mutation == "signal":
        source = source.replace(
            "root.wallpaperChanged(screenName, path);",
            "// staged RED: omit wallpaper notification",
        )
    elif mutation == "list":
        source = source.replace(
            "root.wallpaperLists[screenName] = files;",
            "// staged RED: omit scanner list update",
        )
    write(directory, "qs.Services.UI", {"WallpaperService": source})
    shutil.copyfile(
        ROOT / "Tests/Qml/WallpaperServiceHarness.qml", directory / "tst_wallpaper.qml"
    )


def behavior(directory, mutation):
    stage_runtime(directory, mutation)
    env = os.environ.copy()
    for key in (
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "NIRI_SOCKET",
        "HYPRLAND_INSTANCE_SIGNATURE",
        "QML_IMPORT_PATH",
        "QML2_IMPORT_PATH",
    ):
        env.pop(key, None)
    for key, name in (
        ("HOME", "home"),
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_CACHE_HOME", "cache"),
        ("XDG_DATA_HOME", "data"),
        ("XDG_RUNTIME_DIR", "runtime"),
    ):
        path = directory / name
        path.mkdir(mode=0o700)
        env[key] = str(path)
    env.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent-wallpaper-session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent-wallpaper-system",
    )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-import",
            str(directory),
            "-input",
            str(directory / "tst_wallpaper.qml"),
            "-o",
            "-,txt",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=45,
        check=False,
        cwd=directory,
    )
    output = result.stdout + result.stderr
    (directory / "behavior.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0, f"behavior exit {result.returncode}"
    assert "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--mutation", choices=("signal", "list"))
    args = parser.parse_args()
    assert not args.mutation or args.mode == "behavior", (
        "Mutations are behavior-only RED controls"
    )
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    # No settings test occurs: all Settings/FileView operations are inert mocks.
    # Read-only hash checks additionally prove host settings bytes stayed intact.
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = args.artifacts / "settings-backup.json"
    backup.write_bytes(original)
    backup.chmod(0o600)
    digest = hashlib.sha256(original).hexdigest()
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    try:
        if args.mode == "lint":
            lint(args.artifacts)
        else:
            behavior(args.artifacts, args.mutation)
    finally:
        assert settings.read_bytes() == original, "Host settings changed"
        assert backup.read_bytes() == original, "Settings backup changed"


if __name__ == "__main__":
    main()
