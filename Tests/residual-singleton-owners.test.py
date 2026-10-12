#!/usr/bin/env python3
"""Three real singleton owners: strict scoped lint and sandboxed state lifecycle."""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = tuple(Path(f"Commons/{name}.qml") for name in ("Icons", "Settings", "Time"))


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(directory, environment, isolation, argv, timeout=60):
    result = subprocess.run(
        isolation.sandbox_command(directory, argv),
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    print(result.stdout + result.stderr, end="", flush=True)
    return result


def lint(directory, environment, isolation):
    helper("media-mini-warnings.test.py").stage_modules(directory)
    failures = []
    for target in TARGETS:
        limit = 1 if target.stem == "Settings" else 0
        result = run(
            directory,
            environment,
            isolation,
            [
                "/usr/lib/qt6/bin/qmllint",
                "--unqualified",
                "error",
                # Qt counts non-rendered diagnostics toward --max-warnings.
                # Settings' visible residual is enforced by the exact counter;
                # owner diagnostics remain errors, never disabled/demoted.
                *(["--max-warnings", "0"] if not limit else []),
                "-I",
                str(directory),
                str(directory / "qs" / target),
            ],
        )
        output = result.stdout + result.stderr
        counts = Counter(
            re.findall(r"\[([^]]+)\]", line)[-1]
            for line in output.splitlines()
            if line.startswith(("Warning:", "Error:"))
        )
        expected = {"missing-property": 1} if limit else {}
        print(target, "RESIDUAL", dict(counts), "EXIT", result.returncode)
        if counts != expected or result.returncode:
            failures.append((str(target), dict(counts), result.returncode))
    assert not failures, failures


def stage_runtime(directory, shadow):
    helper("settings-singleton-warnings.test.py").stage_runtime(directory)
    writer = helper("media-mini-warnings.test.py")
    commons = directory / "Commons"
    for name in ("Icons", "IconsTabler", "Time"):
        shutil.copyfile(ROOT / f"Commons/{name}.qml", commons / f"{name}.qml")
    writer.write_singleton(commons, "I18n", "function tr(key) { return key; }")
    writer.write_singleton(
        directory / "Services/System",
        "SoundService",
        "property int stops: 0\nproperty int plays: 0\n"
        "function stopSound(name) { stops++; }\n"
        "function playSound(name, options) { plays++; }",
    )
    font = next(Path("/usr/share/fonts").rglob("*.ttf"))
    destination = directory / "Assets/Fonts/tabler/tabler-icons.ttf"
    destination.parent.mkdir(parents=True)
    shutil.copyfile(font, destination)
    if shadow:
        # Deliberate dynamic-scope collisions; observable state must still change
        # through the lexical singleton owner, never these callback-local members.
        replacements = {
            "Icons": (
                "target: Quickshell",
                'target: Quickshell\n    function reloadFont() { throw new Error("SHADOW_RELOAD"); }',
            ),
            "Time": (
                "id: updateTimer",
                'id: updateTimer\n    function updateTime(date) { throw new Error("SHADOW_CLOCK"); }',
            ),
            "Settings": (
                "onAdapterUpdated:",
                "property QtObject saveTimer: QtObject {}\n      onAdapterUpdated:",
            ),
        }
        for name, (before, after) in replacements.items():
            path = commons / f"{name}.qml"
            source = path.read_text()
            assert source.count(before) == 1
            path.write_text(source.replace(before, after))
    shutil.copyfile(
        ROOT / "Tests/Qml/ResidualSingletonOwnersHarness.qml", directory / "shell.qml"
    )


def runtime(directory, environment, isolation, shadow):
    stage_runtime(directory, shadow)
    config = directory / "config"
    cache = directory / "cache"
    config.mkdir(mode=0o700)
    cache.mkdir(mode=0o700)
    environment.update(
        NOCTALIA_CONFIG_DIR=str(config) + "/",
        NOCTALIA_CACHE_DIR=str(cache) + "/",
        NOCTALIA_SETTINGS_FILE=str(config / "settings.json"),
    )
    # Fresh-process initialization, deferred persistence, then fresh hydration.
    for mode in ("create", "reload"):
        environment["OWNER_CASE"] = mode
        trace_path = directory / f"{mode}.trace"
        result = subprocess.run(
            [
                "strace",
                "-f",
                "-qq",
                "-s",
                "512",
                "-e",
                "trace=%file,%network",
                "-o",
                str(trace_path),
                *isolation.sandbox_command(
                    directory,
                    [
                        "quickshell",
                        "--no-color",
                        "-p",
                        str(directory / "shell.qml"),
                    ],
                ),
            ],
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
        )
        output = result.stdout + result.stderr
        print(output, end="", flush=True)
        trace = trace_path.read_text()
        assert not re.search(r'openat\(.*"/home/osso/.*= [0-9]+', trace), (
            "host home opened"
        )
        assert not re.search(r"connect\(.*sa_family=AF_INET6?[,}]", trace), (
            "network attempted"
        )
        assert result.returncode == 0 and f"OWNER_PASS {mode}" in output, output
        assert not re.search(
            r"ReferenceError|TypeError| WARN | ERROR |SHADOW_|OWNER_FAIL", output
        ), output
        settings = json.loads((config / "settings.json").read_text())
        assert settings["audio"]["volumeStep"] == 17
        assert settings["ui"]["fontDefault"] == "Owner Fixture Sans"
        if mode == "create":
            persisted = settings
        else:
            assert settings == persisted, "fresh hydration changed persisted state"
    print("OWNER_RUNTIME_AUDIT_PASS: host config absent; fresh persistence preserved")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument("--shadow", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="owner-") as temporary:
        directory = Path(temporary)
        isolation = helper("wallpaper-tab-warnings.test.py")
        isolation.install_audit(directory)
        environment = isolation.isolated_environment(directory)
        # Prove both read and write denial before any child starts.
        for flags in ("rb", "wb"):
            try:
                open("/home/osso/.config/noctalia/settings.json", flags)
            except PermissionError:
                print("OWNER_AUDIT_DENIED", flags)
            else:
                raise AssertionError("host settings access allowed")
        (directory / "probe.py").write_text(
            "import os\nfor flags in (os.O_RDONLY, os.O_WRONLY):\n"
            '    try: fd = os.open("/home/osso/.config/noctalia/settings.json", flags)\n'
            '    except OSError: print("CHILD_CONFIG_DENIED", flags)\n'
            '    else: os.close(fd); raise AssertionError("host config exposed")\n'
        )
        probe = run(
            directory, environment, isolation, ["python3", str(directory / "probe.py")]
        )
        assert probe.returncode == 0 and probe.stdout.count("CHILD_CONFIG_DENIED") == 2
        if args.mode == "lint":
            lint(directory, environment, isolation)
        else:
            runtime(directory, environment, isolation, args.shadow)


if __name__ == "__main__":
    main()
