"""Production widget-loader proof with private modules and denied host config.

Runtime uses synthetic widget components, not desktop widgets or services.
Static lint uses production modules. Both execute inside a network-isolated
sandbox masking real config parents; staging never reads real settings.
"""

import argparse
import errno
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/ControlCenter/ControlCenterWidgetLoader.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_command(command, directory, environment):
    result = subprocess.run(
        command,
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    return result.returncode, output


def deny_config(config_parent):
    for parent in ("/home/osso", config_parent):
        assert any(
            line.split()[4] == parent and " - tmpfs " in line
            for line in Path("/proc/self/mountinfo").read_text().splitlines()
        )
        for relative in ("noctalia/settings.json", "noctalia"):
            path = parent + ("/.config/" if parent == "/home/osso" else "/") + relative
            try:
                descriptor = os.open(path, os.O_RDONLY)
            except OSError as error:
                assert error.errno == errno.EACCES, (path, error)
            else:
                os.close(descriptor)
                raise AssertionError(f"real config accessible: {path}")
            print("CONFIG_ACCESS_DENIED", path, "EACCES")


def stage_runtime(directory, mutation, owner_shadow):
    modules = helper("about-tab-warnings.test.py")
    source = (ROOT / TARGET).read_text()
    if mutation:
        # Reverse only owner qualifications in the private production copy.
        source = source.replace("root.widgetProps", "widgetProps")
        source = source.replace("root.widgetScreen", "widgetScreen")
    if owner_shadow:
        # Deliberately shadow outer names at the lexical boundary under test.
        source = source.replace(
            "id: loader",
            """id: loader
    property var widgetProps: ({caption: "wrong-owner"})
    property ShellScreen widgetScreen: null""",
        )
    modules.write_module(
        directory, "qs.LoaderProof", {"ControlCenterWidgetLoader": source}
    )
    modules.write_module(
        directory,
        "Quickshell",
        {"ShellScreen": "import QtQuick\nQtObject { property string name }"},
    )
    modules.write_module(
        directory,
        "qs.Commons",
        {
            "Logger": modules.singleton("""property var warnings: []
function w(...args) { warnings = warnings.concat([args]); }""")
        },
    )
    modules.write_module(
        directory,
        "qs.Services.UI",
        {
            "ControlCenterWidgetRegistry": """pragma Singleton
import QtQuick
QtObject {
  property var widgets: ({})
  function getWidget(id) { return widgets[id] || null; }
  function hasWidget(id) { return id in widgets; }
}"""
        },
    )
    harness = directory / "tst_loader.qml"
    harness.write_text(
        (ROOT / "Tests/Qml/ControlCenterWidgetLoaderHarness.qml").read_text()
    )
    return harness


def lint_harness(directory, harness, environment, inject_warning):
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "id: host",
                "id: host\n  property int injectedWarning: host.missingLintProbe",
                1,
            )
        )
    code, output = run_command(
        [
            "/usr/lib/qt6/bin/qmllint",
            "--bare",
            "-I",
            str(directory),
            "-I",
            "/usr/lib/qt6/qml",
            "--max-warnings",
            "0",
            "--json",
            "-",
            str(harness),
        ],
        directory,
        environment,
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    print("LOADER_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0, "injected warning not diagnosed"
        assert code != 0, "injected warning accepted"
    else:
        assert code != 0 or warnings == 0, "warnings accepted by strict lint"
    return code


def sandboxed(args):
    deny_config(args.config_parent)
    directory = args.sandbox
    home = directory / "home"
    home.mkdir()
    runtime = directory / "runtime"
    runtime.mkdir(mode=0o700)
    environment = {
        "PATH": "/usr/bin",
        "LANG": "C.UTF-8",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_DATA_HOME": str(home / "data"),
        "XDG_RUNTIME_DIR": str(runtime),
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "QML_DISABLE_DISK_CACHE": "1",
    }
    if args.mode == "lint":
        helper("media-mini-warnings.test.py").stage_modules(directory)
        code, output = run_command(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / TARGET),
            ],
            directory,
            environment,
        )
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
        print("LOADER_WARNINGS", len(warnings), dict(counts))
        assert code == 0, code
        assert counts == {"missing-property": 2}, dict(counts)
        return
    harness = stage_runtime(directory, args.mutation, args.owner_shadow)
    if args.mode == "lint-harness":
        raise SystemExit(
            lint_harness(directory, harness, environment, args.inject_warning)
        )
    code, output = run_command(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(harness),
            "-import",
            str(directory),
        ],
        directory,
        environment,
    )
    assert code == 0 and "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output
    print("LOADER_RUNTIME_PASS")


def audit_config_access(trace, config_parent):
    for parent in ("/home/osso/.config", config_parent):
        for relative in ("noctalia/settings.json", "noctalia"):
            path = parent + "/" + relative
            access = [
                line
                for line in trace.splitlines()
                if re.search(r"\bopen(?:at2?)?\(", line) and '"' + path + '"' in line
            ]
            assert all("= -1 EACCES" in line for line in access), access


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("runtime", "lint", "lint-harness"))
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--mutation", action="store_true")
    parser.add_argument("--owner-shadow", action="store_true")
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--config-parent", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    if args.sandbox:
        sandboxed(args)
        return
    config_parent = str(Path.home() / ".config")
    with tempfile.TemporaryDirectory(prefix="noctalia-loader-proof-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        command = [
            "bwrap",
            "--die-with-parent",
            "--unshare-all",
            "--new-session",
            "--ro-bind",
            "/",
            "/",
            "--tmpfs",
            "/syncthing",
            "--ro-bind",
            str(ROOT),
            str(ROOT),
            # Replace read-only outer /tmp before creating the HOME config mask.
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/run",
            "--perms",
            "000",
            "--tmpfs",
            "/home/osso",
            "--perms",
            "000",
            "--tmpfs",
            config_parent,
            "--bind",
            temporary,
            temporary,
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--chdir",
            temporary,
            "--",
            "/usr/bin/python3",
            str(Path(__file__).resolve()),
            args.mode,
            "--sandbox",
            temporary,
            "--config-parent",
            config_parent,
        ]
        if args.inject_warning:
            command.append("--inject-warning")
        if args.mutation:
            command.append("--mutation")
        if args.owner_shadow:
            command.append("--owner-shadow")
        audit = directory / "access.trace"
        command = [
            "strace",
            "-f",
            "-qq",
            "-s",
            "512",
            "-e",
            "trace=%file,%network",
            "-o",
            str(audit),
            *command,
        ]
        code, _ = run_command(
            command,
            directory,
            {"PATH": "/usr/bin", "HOME": "/home/osso", "LANG": "C.UTF-8"},
        )
        trace = audit.read_text()
        audit_config_access(trace, config_parent)
        assert not re.search(r"connect\(.*sa_family=AF_INET6?[,}]", trace), (
            "network connection attempted"
        )
        print(
            "CONFIG_AUDIT_PASS zero successful protected opens; sandboxed Qt has no real config or network"
        )
        raise SystemExit(code)


if __name__ == "__main__":
    main()
