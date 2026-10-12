#!/usr/bin/env python3
"""Three-service strict lint and extracted-JS behavior in a masked, private sandbox.

Only qmllint targets are linted. Behavior uses production function/handler bodies,
not QML object instantiation; network, file and process boundaries are inert fakes.
"""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    Path("Services/UI/WallhavenService.qml"),
    Path("Services/Keyboard/EmojiService.qml"),
    Path("Services/Noctalia/UpdateService.qml"),
)


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute(directory, environment, argv):
    isolation = helper("wallpaper-tab-warnings.test.py")
    result = subprocess.run(
        isolation.sandbox_command(directory, argv),
        env=environment,
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=60,
    )
    print(result.stdout, end="")
    print(result.stderr, end="")
    return result


def lint(directory, environment):
    helper("media-mini-warnings.test.py").stage_modules(directory)
    failures = []
    for target in TARGETS:
        result = execute(
            directory,
            environment,
            [
                "/usr/lib/qt6/bin/qmllint",
                "--max-warnings",
                "0",
                "--json",
                "-",
                "-I",
                str(directory),
                str(directory / "qs" / target),
            ],
        )
        reports = json.loads(result.stdout)["files"]
        diagnostics = [
            warning
            for report in reports
            for warning in report["warnings"]
            if warning["type"] in ("warning", "error")
        ]
        counts = Counter(warning["id"] for warning in diagnostics)
        print(
            target,
            "ALL_DIAGNOSTICS",
            len(diagnostics),
            dict(counts),
            "EXIT",
            result.returncode,
        )
        if diagnostics or result.returncode:
            failures.append((str(target), dict(counts), result.returncode))
    assert not failures, failures


def behavior(directory, environment, negative):
    for target in TARGETS:
        path = directory / target
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / target, path)
    tests = directory / "Tests"
    tests.mkdir()
    for name in (
        "qml-test-utils.js",
        "update-service-fixtures.test.js",
        "remaining-service-hoisting.test.js",
        "wallhaven-service-guards.test.js",
        "emoji-service-guards.test.js",
        "update-service-guards.test.js",
    ):
        shutil.copyfile(ROOT / "Tests" / name, tests / name)
    if negative:
        mutations = (
            (
                TARGETS[0],
                "var response = JSON.parse(xhr.responseText);",
                "{ const response = JSON.parse(xhr.responseText); }",
            ),
            (
                TARGETS[1],
                'var category = emoji.category || "other";',
                '{ const category = emoji.category || "other"; }',
            ),
            (
                TARGETS[2],
                "for (var i = 0; i < length; i++)",
                "for (const i = 0; i < length; i++)",
            ),
        )
        for target, before, after in mutations:
            path = directory / target
            original = path.read_text()
            # Accept either side of the production lexical-declaration cleanup.
            candidates = (
                before,
                before.replace("var ", "const "),
                before.replace("var ", "let "),
            )
            match = next(candidate for candidate in candidates if candidate in original)
            assert original.count(match) == 1
            path.write_text(original.replace(match, after))
            result = execute(
                directory,
                environment,
                [
                    "/usr/bin/node",
                    str(tests / "remaining-service-hoisting.test.js"),
                    target.stem,
                ],
            )
            expected_errors = {
                "WallhavenService": "AssertionError",
                "EmojiService": "ReferenceError: category is not defined",
                "UpdateService": "TypeError: Assignment to constant variable",
            }
            assert (
                result.returncode != 0 and expected_errors[target.stem] in result.stderr
            ), result
            print("SCOPING_CONTROL_REJECTED", target)
            path.write_text(original)
    else:
        for name in (
            "remaining-service-hoisting.test.js",
            "update-service-fixtures.test.js",
            "wallhaven-service-guards.test.js",
            "emoji-service-guards.test.js",
            "update-service-guards.test.js",
        ):
            result = execute(
                directory, environment, ["/usr/bin/node", str(tests / name)]
            )
            assert result.returncode == 0, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior", "negative"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(
        prefix="noctalia-remaining-services-"
    ) as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation = helper("wallpaper-tab-warnings.test.py")
        isolation.install_audit(directory)
        environment = isolation.isolated_environment(directory)
        if args.mode == "lint":
            lint(directory, environment)
        else:
            behavior(directory, environment, args.mode == "negative")


if __name__ == "__main__":
    main()
