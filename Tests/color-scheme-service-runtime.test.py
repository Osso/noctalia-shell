#!/usr/bin/env python3
"""Bounded production singleton lint and real FileView/Process ordering tests."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Services/Theming/ColorSchemeService.qml")
SETTINGS = Path("/home/osso/.config/noctalia/settings.json")
KEYS = (
    "mPrimary mOnPrimary mSecondary mOnSecondary mTertiary mOnTertiary "
    "mError mOnError mSurface mOnSurface mSurfaceVariant mOnSurfaceVariant "
    "mOutline mShadow mHover mOnHover"
).split()


def write_module(directory, uri, sources):
    module = directory.joinpath(*uri.removeprefix("qs.").split("."))
    module.mkdir(parents=True, exist_ok=True)
    declarations = []
    for name, source in sources.items():
        (module / f"{name}.qml").write_text(source)
        prefix = "singleton " if source.startswith("pragma Singleton") else ""
        declarations.append(f"{prefix}{name} 1.0 {name}.qml\n")
    (module / "qmldir").write_text(f"module {uri}\n" + "".join(declarations))


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def lint(directory):
    spec = importlib.util.spec_from_file_location(
        "staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    staging = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(staging)
    staging.stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "--json",
            "-",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=ROOT,
    )
    (directory / "lint.json").write_text(result.stdout)
    (directory / "lint.stderr").write_text(result.stderr)
    diagnostics = json.loads(result.stdout)["files"][0]["warnings"]
    warnings = [w for w in diagnostics if w["type"] == "warning"]
    for warning in warnings:
        print(warning["line"], warning["id"], warning["message"])
    print("COLOR_SCHEME_LINT_WARNINGS", len(warnings))
    targeted = [w for w in warnings if w["id"] in ("unqualified", "missing-property")]
    print("COLOR_SCHEME_TARGET_WARNINGS", len(targeted))
    assert not targeted, targeted
    assert result.returncode == 0, result.stderr


def stage_runtime(directory, mode):
    config = directory / "config"
    bundled = directory / "bundled"
    downloaded = config / "colorschemes"
    for path in (config, bundled, downloaded, directory / "bin"):
        path.mkdir(parents=True)
    palettes = {
        name: {key: color for key in KEYS}
        for name, color in (
            ("dark", "#123456"),
            ("light", "#abcdef"),
            ("updated", "#654321"),
            ("switched", "#789abc"),
        )
    }
    rose = downloaded / "Rosepine.json"
    rose.write_text(json.dumps({"dark": palettes["dark"], "light": palettes["light"]}))
    zebra = bundled / "Zebra.json"
    zebra.write_text(json.dumps(palettes["switched"]))
    (config / "colors.json").write_text(json.dumps(palettes["dark"]))
    write_module(
        directory,
        "qs.Services.Theming",
        {
            "ColorSchemeService": (ROOT / TARGET).read_text(),
            "AppThemeService": singleton(
                "property int generations: 0\nfunction generateFromPredefinedScheme(data) { generations++; }"
            ),
        },
    )
    write_module(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                "property string configDir: " + json.dumps(str(config) + "/") + "\n"
                "component ColorSchemeSettings: QtObject {\n"
                "property bool darkMode: true\nproperty bool useWallpaperColors: false\n"
                "property string predefinedScheme: " + json.dumps(str(rose)) + "\n"
                "property bool generateTemplatesForPredefined: true\n}\n"
                "component FixtureSettings: QtObject {\n"
                "property ColorSchemeSettings colorSchemes: ColorSchemeSettings {}\n"
                "property var templates: ({terminal: true})\n}\n"
                "property FixtureSettings data: FixtureSettings {}"
            ),
            "Logger": singleton(
                "property var messages: []\nfunction record(args) { messages = messages.concat([args.join(' ')]); }\nfunction i(...args) { record(args); }\nfunction d(...args) { record(args); }\nfunction e(...args) { record(args); }"
            ),
            "I18n": singleton("function tr(key) { return key; }"),
        },
    )
    write_module(
        directory,
        "qs.Services.UI",
        {
            "ToastService": singleton(
                "property int notices: 0\nproperty int errors: 0\nfunction showNotice(title, description, icon) { notices++; }\nfunction showError(title, description) { errors++; }"
            )
        },
    )
    # Real finder by default; controlled stream/exit ordering for the boundary cases.
    finder = directory / "bin/find"
    finder.write_text(
        "#!/usr/bin/python3\nimport os, sys, time\n"
        + (
            "os.execv('/usr/bin/find', ['/usr/bin/find', *sys.argv[1:]])\n"
            if mode == "normal"
            else "print("
            + repr(str(rose))
            + ", flush=True)\nos.close(1)\ntime.sleep(0.6)\n"
            "print('synthetic stderr after stdout EOF', file=sys.stderr, flush=True)\n"
            "time.sleep(0.2)\nsys.exit(" + ("1" if mode == "error" else "0") + ")\n"
        )
    )
    finder.chmod(0o700)
    mutate = directory / "mutate.py"
    mutate.write_text(
        "from pathlib import Path\nimport json\n"
        f"Path({str(rose)!r}).write_text({json.dumps({'dark': palettes['updated'], 'light': palettes['light']})!r})\n"
        f"Path({str(bundled / 'Amber.json')!r}).write_text({json.dumps(palettes['light'])!r})\n"
    )
    harness = (ROOT / "Tests/Qml/ColorSchemeServiceHarness.qml").read_text()
    for key, value in {
        "MODE": mode,
        "BUNDLED": str(bundled),
        "ROSE": str(rose),
        "ZEBRA": str(zebra),
        "MUTATOR": str(mutate),
    }.items():
        harness = harness.replace(json.dumps("@" + key + "@"), json.dumps(value))
    (directory / "shell.qml").write_text(harness)


def lint_harness(directory):
    stage_runtime(directory, "normal")
    # Quickshell maps qs.* to the shell root; qmllint needs that URI explicitly.
    imports = directory / "imports"
    imports.mkdir()
    (imports / "qs").symlink_to(directory.resolve(), target_is_directory=True)
    return check_harness(imports, directory / "shell.qml")


def runtime(directory):
    failures = []
    for mode in ("normal", "early", "error"):
        case = directory / mode
        case.mkdir(mode=0o700)
        stage_runtime(case, mode)
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(
                ("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_", "QS_")
            )
            and key not in ("DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "HOME")
        }
        for variable in (
            "HOME",
            "XDG_CONFIG_HOME",
            "XDG_CACHE_HOME",
            "XDG_DATA_HOME",
            "XDG_STATE_HOME",
            "XDG_RUNTIME_DIR",
        ):
            path = case / variable
            path.mkdir(mode=0o700)
            environment[variable] = str(path)
        environment.update(
            QT_QPA_PLATFORM="offscreen",
            QT_QUICK_BACKEND="software",
            DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent",
            DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent",
            PATH=str(case / "bin") + ":/usr/bin",
        )
        process = subprocess.Popen(
            ["/usr/bin/quickshell", "--no-color", "-p", str(case / "shell.qml")],
            cwd=case,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=15)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # Process group already exited, including fixture children.
            process.wait()
        output = stdout + stderr
        (case / "runtime.log").write_text(output)
        print(output, end="")
        has_diagnostics = re.search(
            r"\b(?:WARN|ERROR|FATAL)\b|ReferenceError|TypeError|Binding loop", output
        )
        if (
            process.returncode != 0
            or "COLOR_SCHEME_RUNTIME_PASS " + mode not in output
            or has_diagnostics
        ):
            failures.append((mode, process.returncode, str(case / "runtime.log")))
    assert not failures, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "runtime"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700)
    if args.mode == "lint-harness":
        return lint_harness(args.artifacts)
    original = SETTINGS.read_bytes()
    backup = args.artifacts / "settings.json.backup"
    backup.write_bytes(original)
    backup.chmod(0o600)
    digest = hashlib.sha256(original).digest()
    assert hashlib.sha256(backup.read_bytes()).digest() == digest
    try:
        (lint if args.mode == "lint" else runtime)(args.artifacts)
    finally:
        assert SETTINGS.read_bytes() == original, "real settings changed"
        assert hashlib.sha256(backup.read_bytes()).digest() == digest, "backup changed"


if __name__ == "__main__":
    raise SystemExit(main())
