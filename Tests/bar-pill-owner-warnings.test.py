#!/usr/bin/env python3
"""Bounded BarPill owner proof; parent runner and Qt child cannot access config.

Only the launcher resolves config symlink metadata. All staging, lint and runtime
execute inside bubblewrap with both config parents hidden and desktop IO removed.
Production pills remain unchanged; the negative control mutates a staged copy.
"""

import argparse
from collections import Counter
import errno
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WIDGET = Path("Modules/Bar/Extras/BarPill.qml")


def load_helper():
    spec = importlib.util.spec_from_file_location(
        "bar_pill", ROOT / "Tests/bar-pill-warnings.test.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def run_command(command, directory, environment):
    result = subprocess.run(
        command,
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    return result.returncode, output


def run_sandboxed(args):
    directory = args.sandbox
    # A direct invocation must fail before staging or importing fixture helpers.
    mounts = Path("/proc/self/mountinfo").read_text()
    for masked in ("/home/osso", args.config_parent):
        assert any(
            line.split()[4] == masked and " - tmpfs " in line
            for line in mounts.splitlines()
        ), f"config parent is not masked: {masked}"
    for settings in (
        "/home/osso/.config/noctalia/settings.json",
        args.config_parent + "/noctalia/settings.json",
    ):
        try:
            descriptor = os.open(settings, os.O_RDONLY)
        except OSError as error:
            assert error.errno == errno.EACCES, (settings, error)
        else:
            os.close(descriptor)
            raise AssertionError(f"real settings are accessible: {settings}")
        print("CONFIG_ACCESS_DENIED", settings, "EACCES")
    helper = load_helper()
    environment = helper.load_helper("media-mini-warnings").isolate_environment(
        directory
    )
    if args.mode == "lint":
        helper.load_helper("media-mini-warnings").stage_modules(directory)
        code, output = run_command(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / WIDGET),
            ],
            directory,
            environment,
        )
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
        assert code == 0, code
        assert counts == {"missing-property": 8}, dict(counts)
        print("BAR_PILL_OWNER_LINT", dict(counts))
        return
    helper.stage_runtime(directory)
    (directory / "tst_bar_pill.qml").unlink()
    harness = args.harness or ROOT / "Tests/Qml/BarPillOwnerHarness.qml"
    (directory / "tst_bar_pill_owner.qml").write_text(harness.read_text())
    if args.mutation:
        staged = directory / "qs" / WIDGET
        source = staged.read_text()
        assert source.count("text: root.text") == 2
        staged.write_text(source.replace("text: root.text", "text: text"))
    code, output = run_command(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory),
            "-import",
            str(directory),
        ],
        directory,
        environment,
    )
    assert code == 0, f"BarPill owner runtime exit {code}"
    assert "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output
    print("BAR_PILL_OWNER_RUNTIME_PASS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument("--mutation", action="store_true")
    parser.add_argument("--harness", type=Path)
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--config-parent", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.sandbox:
        run_sandboxed(args)
        return
    config_parent = str((Path.home() / ".config/noctalia").resolve().parent)
    with tempfile.TemporaryDirectory(prefix="noctalia-bar-pill-owner-") as temporary:
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
            "--perms",
            "000",
            "--tmpfs",
            "/home/osso",
            "--perms",
            "000",
            "--tmpfs",
            config_parent,
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/run",
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
        if args.harness:
            separator = command.index("--")
            command[separator:separator] = [
                "--ro-bind",
                str(args.harness.resolve()),
                "/bar-pill-harness.qml",
            ]
            command.extend(["--harness", "/bar-pill-harness.qml"])
        if args.mutation:
            command.append("--mutation")
        environment = {"PATH": "/usr/bin", "HOME": "/home/osso", "LANG": "C.UTF-8"}
        code, _ = run_command(command, directory, environment)
        raise SystemExit(code)


if __name__ == "__main__":
    main()
