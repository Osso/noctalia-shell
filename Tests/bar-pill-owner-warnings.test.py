#!/usr/bin/env python3
"""Bounded BarPill owner proof; parent runner and Qt child cannot access config.

All staging, lint and runtime execute inside bubblewrap with host home/sync
roots hidden, a read-only repository and private temporary/runtime filesystems.
Production pills remain unchanged; the negative control mutates a staged copy.
"""

import argparse
import errno
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDGET = Path("Modules/Bar/Extras/BarPill.qml")


def load_helper():
    sys.path.insert(0, str(ROOT / "Tests"))
    spec = importlib.util.spec_from_file_location(
        "bar_pill", ROOT / "Tests/bar-pill-warnings.test.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def run_command(command, directory, environment):
    result = subprocess.run(
        command,
        check=False,
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="" if output.endswith("\n") else "\n")
    return result.returncode, output


def run_sandboxed(args):
    directory = args.sandbox
    # A direct invocation must fail before staging or importing fixture helpers.
    mounts = Path("/proc/self/mountinfo").read_text()
    for masked in ("/home", "/syncthing", "/tmp", "/run"):
        assert any(
            line.split()[4] == masked and " - tmpfs " in line
            for line in mounts.splitlines()
        ), f"host path is not masked: {masked}"
    assert os.stat("/home").st_mode & 0o777 == 0, "home mask is not locked"
    assert any(
        line.split()[4] == str(ROOT) and "ro" in line.split()[5].split(",")
        for line in mounts.splitlines()
    ), "repository rebind is not read-only"
    probe = "/home/bar-pill-isolation-probe"
    try:
        descriptor = os.open(probe, os.O_RDONLY)
    except OSError as error:
        assert error.errno == errno.EACCES, (probe, error)
    else:
        os.close(descriptor)
        raise AssertionError("host home mask permits file access")
    print("CONFIG_ACCESS_DENIED", probe, "EACCES")
    print("BAR_PILL_HOST_MASKED", flush=True)
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
    if args.mode == "lint-harness":
        code, _ = run_command(
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
                str(directory / "tst_bar_pill_owner.qml"),
            ],
            directory,
            environment,
        )
        assert code == 0, f"BarPill fixture lint exit {code}"
        print("BAR_PILL_FIXTURE_LINT_PASS")
        return
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
    parser.add_argument("mode", choices=("lint", "lint-harness", "runtime"))
    parser.add_argument("--mutation", action="store_true")
    parser.add_argument("--harness", type=Path)
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.sandbox:
        run_sandboxed(args)
        return
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
            "/home",
            "--tmpfs",
            "/syncthing",
            "--ro-bind",
            str(ROOT),
            str(ROOT),
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
            str(Path(__file__).absolute()),
            args.mode,
            "--sandbox",
            temporary,
        ]
        script = Path(__file__).absolute()
        if not script.is_relative_to(ROOT):
            separator = command.index("--")
            command[separator:separator] = ["--bind", str(script), str(script)]
        if args.harness:
            harness_target = str(directory / "supplied-harness.qml")
            separator = command.index("--")
            command[separator:separator] = [
                "--bind",
                str(args.harness.absolute()),
                harness_target,
            ]
            command.extend(["--harness", harness_target])
        if args.mutation:
            command.append("--mutation")
        environment = {"PATH": "/usr/bin", "HOME": "/home/osso", "LANG": "C.UTF-8"}
        code, _ = run_command(command, directory, environment)
        raise SystemExit(code)


if __name__ == "__main__":
    main()
