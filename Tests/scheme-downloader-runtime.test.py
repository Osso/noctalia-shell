#!/usr/bin/env python3
"""Targeted lint and nonvisible production downloader with synthetic transport.

Only XHR construction/DONE are substituted in the staged component. Qt callbacks,
Popup, Timer, and Quickshell Process stay real. Download commands use file-only
fixture curl/wget executables; every writable path belongs to a temporary tree.
"""

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Tabs/ColorScheme/SchemeDownloader.qml")


def load_staging():
    spec = importlib.util.spec_from_file_location(
        "downloader_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    load_staging().stage_modules(directory)
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
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    counts = Counter(
        "block-scope-var-declaration"
        if "var declaration in block scope" in line
        else re.findall(r"\[([^]]+)\]", line)[-1]
        if "[" in line
        else "other"
        for line in warnings
    )
    print("SCHEME_DOWNLOADER_LINT_COUNTS", dict(counts))
    assert not counts, dict(counts)
    assert result.returncode == 0, result.returncode
    print("SCHEME_DOWNLOADER_LINT_PASS")


def write_module(directory, name, sources):
    path = directory / name.removeprefix("qs.").replace(".", "/")
    path.mkdir(parents=True, exist_ok=True)
    declarations = []
    for type_name, source in sources.items():
        (path / f"{type_name}.qml").write_text(source)
        is_singleton = re.search(r"^\s*pragma\s+Singleton\b", source, re.M)
        prefix = "singleton " if is_singleton else ""
        declarations.append(f"{prefix}{type_name} 1.0 {type_name}.qml\n")
    (path / "qmldir").write_text(f"module {name}\n" + "".join(declarations))


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def stage_runtime(directory):
    source = (ROOT / TARGET).read_text()
    source = source.replace("new XMLHttpRequest()", "Transport.createRequest()")
    source = source.replace("XMLHttpRequest.DONE", "Transport.done")
    write_module(directory, "qs.Downloader", {"SchemeDownloader": source})
    style = dict(
        marginXL=16,
        marginL=12,
        marginM=8,
        marginS=4,
        radiusL=12,
        radiusS=4,
        borderM=1,
        borderL=2,
        fontSizeL=14,
        fontSizeM=12,
        fontSizeS=10,
        fontWeightBold=700,
        uiScaleRatio=1,
        animationFast=0,
    )
    colors = [
        "mSurface",
        "mSurfaceVariant",
        "mPrimary",
        "mSecondary",
        "mTertiary",
        "mError",
        "mOnSurface",
        "mOnSurfaceVariant",
        "mOutline",
        "mOnError",
    ]
    transport = (ROOT / "Tests/Qml/SchemeDownloaderTransport.qml").read_text()
    write_module(
        directory,
        "qs.Commons",
        {
            "Style": singleton(
                "\n".join(f"property real {k}: {v}" for k, v in style.items())
            ),
            "NColor": singleton(
                "\n".join(f'property color {k}: "#808080"' for k in colors)
            ),
            "Settings": singleton(
                'property var data: ({colorSchemes: {darkMode: true, predefinedScheme: "Other"}})'
            ),
            "Time": singleton("property real timestamp: 10000"),
            "I18n": singleton(
                "function tr(key, args) { return key + (args ? JSON.stringify(args) : ''); }"
            ),
            "Logger": singleton(
                "function d(...args) {}\nfunction i(...args) {}\nfunction w(...args) {}\nfunction e(...args) {}"
            ),
            "ShellState": singleton(
                "property bool isLoaded: true\nproperty var cache: ({schemes: [], timestamp: 0})\nfunction getColorSchemesList() { return cache; }\nfunction setColorSchemesList(value) { cache = value; }"
            ),
            "Transport": transport,
        },
    )
    write_module(
        directory,
        "qs.Services.Theming",
        {
            "ColorSchemeService": singleton(
                "property string downloadedSchemesDirectory: "
                + json.dumps(str(directory / "output"))
                + "\n"
                "property var schemes: []\nproperty bool scanning: false\nproperty int reloads: 0\n"
                "property string applied: ''\nfunction loadColorSchemes() { reloads++; }\n"
                "function setPredefinedScheme(name) { applied = name; }\nfunction getBasename(name) { return name; }"
            )
        },
    )
    write_module(
        directory,
        "qs.Services.UI",
        {
            "ToastService": singleton(
                "property int notices: 0\nproperty int errors: 0\n"
                "function showNotice(...args) { notices++; }\nfunction showError(...args) { errors++; }"
            )
        },
    )
    write_module(
        directory,
        "qs.Widgets",
        {
            "NText": "import QtQuick\nText { property real pointSize: 12; font.pointSize: pointSize }",
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize }",
            "NIconButton": "import QtQuick\nItem { property string icon; property string tooltipText; signal clicked() }",
            "NBusyIndicator": "import QtQuick\nItem {}",
            "NScrollView": "import QtQuick.Controls\nScrollView { property int verticalPolicy; property int horizontalPolicy; property real handleWidth: 8 }",
        },
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/SchemeDownloaderHarness.qml", directory / "shell.qml"
    )
    fixtures = directory / "fixtures"
    fixtures.mkdir()
    (fixtures / "scheme.json").write_text(
        '{"dark":{"mPrimary":"#123456"},"light":{"mPrimary":"#abcdef"}}'
    )
    (fixtures / "terminal.txt").write_text("synthetic terminal colors\n")
    deleted = directory / "output/delete-me"
    deleted.mkdir(parents=True)
    (deleted / "delete-me.json").write_text("{}")
    # No external URL is accepted, even if production builds an unexpected one.
    executable = directory / "bin"
    executable.mkdir()
    downloader = (
        "#!/usr/bin/python3\n"
        + """import pathlib, sys, urllib.parse
args = sys.argv[1:]
url = urllib.parse.urlparse(args[-1])
root = pathlib.Path(__file__).resolve().parent.parent
if url.scheme != 'file' or url.netloc:
    sys.stderr.write('fixture rejected external URL\\n')
    sys.exit(9)
source = pathlib.Path(urllib.parse.unquote(url.path)).resolve()
flag = '-o' if '-o' in args else '-O'
target = pathlib.Path(args[args.index(flag) + 1]).resolve()
if not source.is_relative_to(root / 'fixtures') or not target.is_relative_to(root / 'output'):
    sys.stderr.write('fixture rejected path\\n')
    sys.exit(9)
target.write_bytes(source.read_bytes())
"""
    )
    for name in ("curl", "wget"):
        path = executable / name
        path.write_text(downloader)
        path.chmod(0o700)


def load_isolation():
    spec = importlib.util.spec_from_file_location(
        "downloader_isolation", ROOT / "Tests/wallpaper-tab-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint_harness(directory, inject=False):
    runtime = directory / "runtime"
    runtime.mkdir()
    stage_runtime(runtime)
    imports = directory / "imports"
    load_staging().stage_modules(imports, source_root=runtime)
    transport = imports / "qs/Commons/Transport.qml"
    if inject:
        source = transport.read_text()
        marker = "QtObject {"
        assert source.count(marker) == 1
        transport.write_text(
            source.replace(
                marker,
                marker
                + "\n    property int injectedWarning: transport.missingLintProbe",
                1,
            )
        )
    isolation = load_isolation()
    result = subprocess.run(
        isolation.sandbox_command(
            directory,
            [
                "/usr/lib/qt6/bin/qmllint",
                "--bare",
                "-I",
                str(imports),
                "-I",
                "/usr/lib/qt6/qml",
                "--max-warnings",
                "0",
                "--json",
                "-",
                str(imports / "qs/shell.qml"),
                str(transport),
            ],
        ),
        cwd=directory,
        env=isolation.isolated_environment(directory),
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="", flush=True)
    diagnostics = json.loads(result.stdout)
    warnings = sum(
        warning["type"] == "warning"
        for item in diagnostics["files"]
        for warning in item["warnings"]
    )
    print("SCHEME_DOWNLOADER_HARNESS_WARNINGS", warnings, "EXIT", result.returncode)
    passed = (
        result.returncode == 0
        and warnings == 0
        and all(item["success"] for item in diagnostics["files"])
    )
    if inject:
        assert not passed and result.returncode != 0, (
            "Injected semantic warning accepted"
        )
        assert "missingLintProbe" in output
        print("SCHEME_DOWNLOADER_HARNESS_WARNING_REJECTED")
        return 0
    return 0 if passed else result.returncode or 1


def runtime(directory):
    stage_runtime(directory)
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_", "QS_"))
        and k
        not in (
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "DBUS_SYSTEM_BUS_ADDRESS",
            "HOME",
        )
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / key.lower()
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        QML_IMPORT_PATH=str(directory),
        PATH=str(directory / "bin") + os.pathsep + os.environ["PATH"],
    )
    settings = Path(environment["HOME"]) / ".config/noctalia/settings.json"
    settings.parent.mkdir(mode=0o700, parents=True)
    original = (ROOT / "Assets/settings-default.json").read_bytes()
    settings.touch(mode=0o600)
    settings.write_bytes(original)
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert backup.read_bytes() == original, "fixture backup bytes differ"
    try:
        result = subprocess.run(
            load_isolation().sandbox_command(
                directory, ["quickshell", "-p", str(directory / "shell.qml")]
            ),
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        assert settings.read_bytes() == original, "fixture settings changed"
        assert backup.read_bytes() == original, "fixture backup changed"
    output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout + result.stderr)
    print(output, end="")
    assert result.returncode == 0, result.returncode
    assert "SCHEME_DOWNLOADER_PASS" in output, output
    assert output.count("SCHEME_DOWNLOADER_REVERSE_DIRECTORY_PASS") == 1, output
    assert not re.search(r" WARN | ERROR |ReferenceError|TypeError", output), output
    assert (directory / "output/aurora/aurora.json").read_bytes() == (
        directory / "fixtures/scheme.json"
    ).read_bytes()
    assert (
        directory / "output/aurora/nested/terminal.txt"
    ).read_text() == "synthetic terminal colors\n"
    assert not (directory / "output/delete-me").exists()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "runtime", "lint-harness", "lint-harness-regression")
    )
    args = parser.parse_args()
    if args.mode in ("lint-harness", "lint-harness-regression"):
        with tempfile.TemporaryDirectory(
            prefix="noctalia-scheme-harness-lint-"
        ) as name:
            raise SystemExit(
                lint_harness(Path(name), inject=args.mode == "lint-harness-regression")
            )
    with tempfile.TemporaryDirectory(prefix="noctalia-scheme-downloader-") as name:
        globals()[args.mode](Path(name))


if __name__ == "__main__":
    main()
