#!/usr/bin/env python3
"""WallpaperService-only lint and isolated QML behavior; no desktop or real I/O.

RED controls mutate private staged copies. Service lint uses real installed
metadata; lint-harness uses exactly the runtime-staged fixture modules. Bubblewrap
masks host config, wallpaper assets, desktop sockets and network. Runtime executes
production service with inert process, folder and persistence boundaries;
it proves lifecycle, ownership and signal ordering, not rendering or real I/O.
"""

import argparse
import importlib.util
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path

from qml_fixture_lint import check_harness

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
    owners = [w for w in warnings if w["id"] == "unqualified"]
    assert not owners, [(w["line"], w["message"]) for w in owners]
    # Pre-existing var hoisting and incomplete FileViewAdapter metadata are
    # outside lexical-owner cleanup; no casts or synthetic metadata hide them.
    assert set(counts) <= {"block-scope-var-declaration", "unresolved-type"}, counts


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
                "property int writes: 0\nproperty var snapshots: []\nproperty var cache: null\nproperty var processes: []"
            ),
            "FileView": """import QtQuick
QtObject {
  id: view
  property string path
  property bool printErrors
  property bool watchChanges
  property QtObject adapter
  property var wallpaperCacheAdapter: ({
    wallpapers: {"DP-1": "/shadow/cache.jpg"}, defaultWallpaper: "/shadow/cache.png"
  })
  signal loaded()
  signal loadFailed(int error)
  function writeAdapter() {
    FixtureIo.snapshots = FixtureIo.snapshots.concat([JSON.parse(JSON.stringify({
      wallpapers: view.adapter.wallpapers, defaultWallpaper: view.adapter.defaultWallpaper
    }))]);
    FixtureIo.writes++;
  }
  Component.onCompleted: FixtureIo.cache = view
}""",
            "JsonAdapter": 'import QtQuick\nQtObject { property var root: ({noctaliaDefaultWallpaper: "/shadow/default.png"}) }',
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
  // A base-object property wins dynamic root lookup in an unbound delegate.
  property QtObject root: QtObject {
    property int scanningCount: 800
    property var wallpaperLists: ({})
    function getMonitorDirectory(screen) { return "/shadow/scanner"; }
    function wallpaperListChanged(screen, count) {}
  }
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
                'property string cacheDir: "/fixture/"\ncomponent WallpaperSettings: QtObject {\n'
                + "\n".join(fields)
                + "\n}\ncomponent FixtureData: QtObject { property WallpaperSettings wallpaper: WallpaperSettings {} }\n"
                + "property FixtureData data: FixtureData {}\nfunction preprocessPath(path) { return path; }"
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
    elif mutation == "owner":
        source = source.replace("WallpaperService.", "root.")
        source = source.replace(
            "wallpaperCacheView.cachedWallpapers", "wallpaperCacheAdapter.wallpapers"
        )
        source = source.replace(
            "wallpaperCacheView.cachedDefaultWallpaper",
            "wallpaperCacheAdapter.defaultWallpaper",
        )
    elif mutation == "cache-load":
        source = source.replace(
            "root.currentWallpapers = wallpaperCacheView.cachedWallpapers || {};",
            "// staged RED: omit cache load",
        )
    elif mutation == "cache-save":
        source = source.replace(
            "wallpaperCacheView.cachedWallpapers = root.currentWallpapers;\n"
            "      wallpaperCacheView.cachedDefaultWallpaper = root.defaultWallpaper;\n"
            "      wallpaperCacheView.writeAdapter();",
            "wallpaperCacheView.writeAdapter();\n"
            "      wallpaperCacheView.cachedWallpapers = root.currentWallpapers;\n"
            "      wallpaperCacheView.cachedDefaultWallpaper = root.defaultWallpaper;",
        )
    elif mutation == "list":
        source = source.replace(
            "WallpaperService.wallpaperLists[screenName] = files;",
            "// staged RED: omit scanner list update",
        )
    write(directory, "qs.Services.UI", {"WallpaperService": source})
    harness = (ROOT / "Tests/Qml/WallpaperServiceHarness.qml").read_text()
    harness = harness.replace(
        "  function init() {",
        """
  // Colliding context names must not own scanner state or cache callbacks.
  property int scanningCount: 900
  property var wallpaperLists: ({"DP-1": ["/shadow/wrong.jpg"]})
  property var currentWallpapers: ({"DP-1": "/shadow/wrong.jpg"})
  property string defaultWallpaper: "/shadow/wrong.png"
  property var wallpaperCacheAdapter: ({wallpapers: {}, defaultWallpaper: "/shadow/cache.png"})

  function initTestCase() {
    tryVerify(() => FixtureIo.cache !== null);
    compare(FixtureIo.cache.adapter.defaultWallpaper, WallpaperService.noctaliaDefaultWallpaper);
  }

  function test_repeatedScanAndRecreatedOwner() {
    for (let cycle = 0; cycle < 3; cycle++) {
      const scanner = FixtureFolders.scanners[0];
      scanner.status = FolderListModel.Null;
      WallpaperService.scanningCount = 0;
      listSpy.clear();
      WallpaperService.refreshWallpapersList();
      compare(scanner.currentDirectory, "/tmp");
      tryCompare(scanner, "currentDirectory", "/fixture/images");
      scanner.status = FolderListModel.Loading;
      compare(WallpaperService.scanningCount, 1);
      compare(WallpaperService.getWallpapersList("DP-1"), []);
      scanner.files = ["cycle" + cycle + ".png"];
      scanner.status = FolderListModel.Ready;
      compare(WallpaperService.getWallpapersList("DP-1"), ["/fixture/images/cycle" + cycle + ".png"]);
      compare(WallpaperService.scanningCount, 0);
      compare(Array.from(listSpy.signalArguments[0]), ["DP-1", 1]);
      Quickshell.screens = [];
      tryCompare(FixtureFolders, "scanners", []);
      Quickshell.screens = [test.firstScreen, test.secondScreen];
      tryVerify(() => FixtureFolders.scanners.length === 2);
    }
    compare(FixtureFolders.scanners[0].root.scanningCount, 800);
    compare(FixtureFolders.scanners[0].root.wallpaperLists, {});
    compare(test.scanningCount, 900);
    compare(test.wallpaperLists["DP-1"], ["/shadow/wrong.jpg"]);
  }

  function test_cacheLoadFailureSaveOrdering() {
    const cache = FixtureIo.cache;
    const writesBefore = FixtureIo.writes;
    WallpaperService.isInitialized = false;
    cache.adapter.wallpapers = {"DP-1": "/fixture/loaded.jpg"};
    cache.adapter.defaultWallpaper = "/fixture/loaded-default.png";
    cache.loaded();
    verify(WallpaperService.isInitialized);
    compare(WallpaperService.getWallpaper("DP-1"), "/fixture/loaded.jpg");
    compare(FixtureIo.writes, writesBefore);
    WallpaperService.changeWallpaper("/fixture/pending.jpg", "DP-1");
    WallpaperService.isInitialized = false;
    cache.loadFailed(1);
    verify(WallpaperService.isInitialized);
    compare(WallpaperService.currentWallpapers, {});
    compare(WallpaperService.defaultWallpaper, "/fixture/loaded-default.png");
    WallpaperService.changeWallpaper("/fixture/final.jpg", "DP-2");
    tryCompare(FixtureIo, "writes", writesBefore + 1);
    const snapshot = FixtureIo.snapshots[FixtureIo.snapshots.length - 1];
    compare(snapshot.wallpapers, {"DP-2": "/fixture/final.jpg"});
    compare(snapshot.defaultWallpaper, "/fixture/loaded-default.png");
    cache.adapter.wallpapers = {};
    cache.adapter.defaultWallpaper = "";
    cache.loaded();
    compare(WallpaperService.defaultWallpaper, WallpaperService.noctaliaDefaultWallpaper);
    compare(WallpaperService.currentWallpapers, {});
    compare(test.currentWallpapers["DP-1"], "/shadow/wrong.jpg");
    compare(cache.wallpaperCacheAdapter.wallpapers["DP-1"], "/shadow/cache.jpg");
    compare(cache.wallpaperCacheAdapter.defaultWallpaper, "/shadow/cache.png");
    compare(test.wallpaperCacheAdapter.defaultWallpaper, "/shadow/cache.png");
    compare(test.defaultWallpaper, "/shadow/wrong.png");
  }

  function init() {""",
    )
    if mutation == "warning":
        harness = harness.replace(
            "  function init() {",
            '  function init() {\n    console.warn("injected-wallpaper-warning");',
        )
    (directory / "tst_wallpaper.qml").write_text(harness)


def lint_harness(directory):
    stage_runtime(directory, None)
    return check_harness(directory, directory / "tst_wallpaper.qml")


def behavior(directory, mutation):
    stage_runtime(directory, mutation)
    assert check_harness(directory, directory / "tst_wallpaper.qml") == 0, (
        "Harness lint failed"
    )
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
    assert "10 passed, 0 failed, 0 skipped" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument(
        "--mutation",
        choices=("signal", "list", "warning", "owner", "cache-load", "cache-save"),
    )
    parser.add_argument("--sandbox", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    assert not args.mutation or args.mode == "behavior", (
        "Mutations are behavior-only RED controls"
    )
    args.artifacts = args.artifacts.absolute()
    if not args.sandbox:
        args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
        command = [
            "bwrap",
            "--die-with-parent",
            "--unshare-all",
            "--new-session",
            "--clearenv",
            "--setenv",
            "PATH",
            "/usr/bin",
            "--setenv",
            "LANG",
            "C.UTF-8",
            "--ro-bind",
            "/usr",
            "/usr",
            "--symlink",
            "usr/lib",
            "/lib",
            "--symlink",
            "usr/lib",
            "/lib64",
            "--symlink",
            "usr/bin",
            "/bin",
            "--dir",
            "/etc",
            "--ro-bind",
            "/etc/fonts",
            "/etc/fonts",
            "--tmpfs",
            "/home",
            "--tmpfs",
            "/syncthing",
            "--tmpfs",
            "/run",
            "--tmpfs",
            "/tmp",
            "--ro-bind",
            str(ROOT),
            str(ROOT),
            "--tmpfs",
            str(ROOT / "Assets/Wallpaper"),
            "--bind",
            str(args.artifacts),
            str(args.artifacts),
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--chdir",
            str(args.artifacts),
            "--",
            "/usr/bin/python3",
            str(Path(__file__).resolve()),
            args.mode,
            "--artifacts",
            str(args.artifacts),
            "--sandbox",
        ]
        if args.mutation:
            command += ["--mutation", args.mutation]
        result = subprocess.run(command, timeout=90, check=False)
        assert result.returncode == 0, f"sandbox exit {result.returncode}"
        return
    assert not Path("/home/osso/.config").exists(), "Host config exposed"
    assert not Path("/run/user").exists(), "Desktop sockets exposed"
    assert not list((ROOT / "Assets/Wallpaper").iterdir()), "Wallpapers exposed"
    if args.mode == "lint-harness":
        return lint_harness(args.artifacts)
    if args.mode == "lint":
        lint(args.artifacts)
    else:
        behavior(args.artifacts, args.mutation)


if __name__ == "__main__":
    raise SystemExit(main())
