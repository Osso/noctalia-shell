#!/usr/bin/env python3
"""Strict installed-metadata lint and sandboxed real ProgramChecker processes.

Only which/sh fixture binaries execute; neither interprets commands nor probes
host executables/directories. Real Quickshell Process/StdioCollector stay intact.
Quickshell 0.3.2 exports Process.stdout as DataStreamParser; only the concrete
StdioCollector exports text. Strict lint uses those installed types unchanged.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Services/System/ProgramCheckerService.qml")
STUB = r"""
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
    const char *name = strrchr(argv[0], '/');
    name = name ? name + 1 : argv[0];
    if (!strcmp(name, "which")) {
        if (argc != 2) return 91;
        if (!strcmp(argv[1], "kitty") || !strcmp(argv[1], "niri")) {
            printf("/inert/%s\n", argv[1]);
            return 0;
        }
        return 1;
    }
    if (strcmp(name, "sh") || argc != 3 || strcmp(argv[1], "-c")) return 92;
    FILE *file = fopen("/state/scenario", "r");
    if (!file) { perror("private scenario"); return 93; }
    int mode = fgetc(file);
    fclose(file);
    if (mode == 'e') {
        puts("vesktop\ncode");
        fputs("inert failure\n", stderr);
        return 7;
    }
    if (mode == 'n') return 0;
    if (strstr(argv[2], "vesktop")) puts(" vesktop\r\ndiscord\nvesktop\nunknown");
    else if (strstr(argv[2], "VSCodium")) puts("code\nvscodium\ncode\nunknown");
    else return 1;
    return 0;
}
"""


def write_module(directory, uri, sources):
    path = directory / uri.replace(".", "/")
    path.mkdir(parents=True, exist_ok=True)
    declarations = []
    for name, source in sources.items():
        (path / f"{name}.qml").write_text(source)
        prefix = "singleton " if source.startswith("pragma Singleton") else ""
        declarations.append(f"{prefix}{name} 1.0 {name}.qml\n")
    (path / "qmldir").write_text(f"module {uri}\n" + "".join(declarations))


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def stage(directory):
    write_module(
        directory,
        "qs.Services.System",
        {"ProgramCheckerService": (ROOT / TARGET).read_text()},
    )
    write_module(
        directory,
        "qs.Commons",
        {
            "Logger": singleton("""property var warnings: []
function d(...args) {}
function w(...args) { warnings = warnings.concat([args.join(" ")]); }""")
        },
    )
    write_module(
        directory,
        "qs.Services.Theming",
        {
            "TemplateRegistry": singleton("""property var discordClients: [
  {name: "vesktop", configPath: "~/.config/vesktop", requiresThemesFolder: true},
  {name: "discord", configPath: "~/.config/discord", requiresThemesFolder: false}]
property var codeClients: [
  {name: "code", configPath: "~/.config/Code"},
  {name: "vscodium", configPath: "~/.config/VSCodium"}]""")
        },
    )
    for name in ("Commons", "Services"):
        (directory / name).symlink_to(Path("qs") / name, target_is_directory=True)
    shutil.copyfile(
        ROOT / "Tests/Qml/ProgramCheckerHarness.qml", directory / "shell.qml"
    )


def lint(directory):
    for path in (directory / "qs" / TARGET, directory / "shell.qml"):
        result = subprocess.run(
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
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        print(result.stdout, end="")
        print(result.stderr, end="")
        report = json.loads(result.stdout)
        warnings = [warning for file in report["files"] for warning in file["warnings"]]
        assert result.returncode == 0 and not warnings, (
            path,
            result.returncode,
            warnings,
        )
    print("PROGRAM_CHECKER_STRICT_LINT_PASS")


def runtime(directory):
    state = directory / "state"
    state.mkdir(mode=0o700)
    (state / "scenario").write_text("success")
    binary = directory / "bin"
    binary.mkdir()
    source = directory / "stub.c"
    source.write_text(STUB)
    subprocess.run(
        ["cc", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary / "which")],
        check=True,
        timeout=30,
    )
    shutil.copyfile(binary / "which", binary / "sh")
    (binary / "sh").chmod(0o700)
    (directory / "fonts.conf").write_text(
        "<fontconfig><dir>/usr/share/fonts</dir><cachedir>/tmp/fonts</cachedir></fontconfig>"
    )
    environment = {
        "PATH": "/fixture/bin",
        "HOME": "/home/fixture",
        "LANG": "C.UTF-8",
        "XDG_CONFIG_HOME": "/home/fixture/config",
        "XDG_CACHE_HOME": "/tmp/cache",
        "XDG_RUNTIME_DIR": "/tmp/runtime",
        "QT_QPA_PLATFORM": "offscreen",
        "FONTCONFIG_FILE": "/fixture/fonts.conf",
        "QT_QUICK_BACKEND": "software",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent",
        "DBUS_SYSTEM_BUS_ADDRESS": "unix:path=/nonexistent",
    }
    result = subprocess.run(
        [
            "/usr/bin/bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--ro-bind",
            "/usr",
            "/usr",
            "--symlink",
            "usr/lib",
            "/lib",
            "--symlink",
            "usr/lib",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/home",
            "--dir",
            "/home/fixture",
            "--dir",
            "/tmp/runtime",
            "--chmod",
            "0700",
            "/tmp/runtime",
            "--ro-bind",
            str(directory),
            "/fixture",
            "--bind",
            str(state),
            "/state",
            "--chdir",
            "/fixture",
            "/usr/bin/quickshell",
            "--no-color",
            "-p",
            "/fixture/shell.qml",
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=45,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    assert (
        result.returncode == 0
        and "PROGRAM_CHECKER_PASS:" in output
        and "PROGRAM_CHECKER_FAIL:" not in output
    ), (result.returncode, output)
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:|\bWARN\b|\bERROR\b",
        output,
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="program-checker-") as temporary:
        directory = Path(temporary)
        os.chmod(directory, 0o700)
        stage(directory)
        if args.mode == "lint":
            lint(directory)
        else:
            runtime(directory)


if __name__ == "__main__":
    main()
