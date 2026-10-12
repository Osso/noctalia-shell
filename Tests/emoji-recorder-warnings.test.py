"""Bounded lint and sandboxed production emoji/recorder behavioral proof."""

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
TARGETS = (
    "Modules/Panels/Launcher/Plugins/EmojiPlugin.qml",
    "Services/Media/ScreenRecorderService.qml",
)


def load_helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    load_helper("media-mini-warnings.test.py").stage_modules(directory)
    for target in TARGETS:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / target),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        counts = Counter(
            (re.findall(r"\[([^]]+)\]", line) or ["uncategorized"])[-1]
            for line in output.splitlines()
            if line.startswith("Warning:")
        )
        print(target, dict(counts), flush=True)
        assert result.returncode == 0 and not counts, (result.returncode, dict(counts))


def stage_runtime(directory, mutation):
    helper = load_helper("workspace-runtime.test.py")
    write, singleton = helper.write_module, helper.singleton
    write(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nItem {}",
            "Quickshell": singleton(
                "property var commands: []\nsignal screensChanged()\nfunction execDetached(argv) { commands = commands.concat([argv]); }"
            ),
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "FixtureIo": singleton(
                "property var commands: []\nproperty var processes: []"
            ),
            "StdioCollector": 'import QtQuick\nQtObject { property string text: "" }',
            "Process": """import QtQuick
Item {
  id: process
  property bool running: false
  property var command: []
  property QtObject stdout
  property QtObject stderr
  signal exited(int exitCode, int exitStatus)
  onRunningChanged: if (running) FixtureIo.commands = FixtureIo.commands.concat([command]);
  function exec(options) { command = options.command; running = true; }
  function complete(code, output, error) {
    if (stdout) stdout.text = output;
    if (stderr) stderr.text = error;
    running = false;
    exited(code, 0);
  }
  Component.onCompleted: FixtureIo.processes = FixtureIo.processes.concat([process]);
}
""",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "I18n": singleton("function tr(key) { return key; }"),
            "Logger": singleton("function i(...args) {}"),
            "Time": singleton(
                'function getFormattedTimestamp() { return "fixture-time"; }'
            ),
            "Settings": singleton("""property var data: ({screenRecorder: {
  videoSource: "focused", directory: "/fixture/videos", frameRate: 60,
  audioCodec: "opus", videoCodec: "h264", audioSource: "both",
  quality: "high", showCursor: true, colorRange: "full"
}})
function preprocessPath(path) { return path; }"""),
        },
    )
    write(
        directory,
        "qs.Services.System",
        {
            "ProgramCheckerService": singleton(
                "property bool gpuScreenRecorderAvailable: false\nsignal checksCompleted()"
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton("property var openedPanel: null"),
            "ToastService": singleton(
                "property var notices: []\nproperty var errors: []\nfunction showNotice(...args) { notices = notices.concat([args]); }\nfunction showError(...args) { errors = errors.concat([args]); }"
            ),
        },
    )
    write(
        directory,
        "qs.Services.Keyboard",
        {
            "EmojiService": singleton("""property bool loaded: false
property var copied: []
property var entries: [
  {name: "Cat", keywords: ["pet", "cat"], category: "animals", emoji: "🐈"},
  {name: "Apple", keywords: ["fruit"], category: "food", emoji: "🍎"}
]
function getEmojisByCategory(category) {
  return category === "recent" ? entries.slice(0, 1) : entries.filter(e => e.category === category);
}
function search(query) { return entries.filter(e => e.name.toLowerCase().includes(query.toLowerCase())); }
function copy(value) { copied = copied.concat([value]); }"""),
        },
    )
    # Concrete Launcher API boundary; no real panels or Settings bootstrap.
    write(
        directory,
        "qs.Modules.Panels.Launcher",
        {
            "Launcher": """import QtQuick
Item {
  property int updates: 0
  property int closes: 0
  property string searchText: ""
  function updateResults() { updates++; }
  function setSearchText(value) { searchText = value; }
  function close() { closes++; }
}""",
        },
    )
    emoji = (ROOT / TARGETS[0]).read_text()
    recorder = (ROOT / TARGETS[1]).read_text()
    if mutation == "emoji":
        emoji = emoji.replace(
            "EmojiService.search(query)", 'EmojiService.search("absent")'
        )
    elif mutation == "command":
        recorder = recorder.replace("-f ${settings.frameRate}", "-f 1")
    elif mutation == "collector":
        recorder = recorder.replace(
            "root.pendingCaptureOptions =", 'root.pendingCaptureOptions = "ignored"; //'
        )
    elif mutation == "exit":
        recorder = recorder.replace(
            'const message = stderr.trim() || I18n.tr("toast.recording.failed-gpu");',
            'const message = "wrong-error";',
        )
    write(directory, "qs.Modules.Panels.Launcher.Plugins", {"EmojiPlugin": emoji})
    write(directory, "qs.Services.Media", {"ScreenRecorderService": recorder})
    shutil.copyfile(
        ROOT / "Tests/Qml/EmojiRecorderWarningsHarness.qml",
        directory / "tst_emoji_recorder.qml",
    )


def lint_harness(directory, inject_warning):
    stage_runtime(directory, None)
    harness = directory / "tst_emoji_recorder.qml"
    if inject_warning:
        source = harness.read_text()
        marker = "id: testCase"
        assert source.count(marker) == 1, "injection owner must be unique"
        harness.write_text(
            source.replace(
                marker,
                marker
                + "\n    property int injectedWarning: testCase.missingLintProbe",
                1,
            )
        )
    isolation = load_helper("grid-list-warnings.test.py")
    code, output = isolation.run_audited(
        directory,
        isolation.isolated_environment(directory),
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
        "emoji-recorder-harness-lint",
    )
    diagnostics = json.loads(output)
    warnings = sum(
        diagnostic["type"] == "warning"
        for entry in diagnostics["files"]
        for diagnostic in entry["warnings"]
    )
    print("EMOJI_RECORDER_HARNESS_WARNINGS", warnings, "EXIT", code, flush=True)
    if inject_warning:
        assert warnings > 0 and code != 0, "injected warning was accepted"
    else:
        assert warnings == 0 and code == 0, "strict harness lint failed"
    return code


def runtime(directory, mutation):
    stage_runtime(directory, mutation)
    environment = {
        "PATH": "/usr/bin",
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/absent",
        "DBUS_SYSTEM_BUS_ADDRESS": "unix:path=/absent",
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "NOCTALIA_CONFIG_DIR",
        "NOCTALIA_CACHE_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    command = [
        "bwrap",
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
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
        "--dir",
        "/etc",
        "--ro-bind",
        "/etc/fonts",
        "/etc/fonts",
        "--bind",
        str(directory),
        str(directory),
        "--chdir",
        str(directory),
        "/usr/bin/python3",
        "-c",
        (
            "import os, pathlib, sys; "
            "assert all(not pathlib.Path(p).exists() for p in "
            "('/home/osso/.config', '/syncthing', '/run/user', '/dev/dri', '/dev/snd')); "
            "assert os.readlink('/proc/self/ns/net') != sys.argv[1]; "
            "print('ISOLATION_PASS', flush=True); "
            "os.execv(sys.argv[2], sys.argv[2:])"
        ),
        os.readlink("/proc/self/ns/net"),
        "/usr/lib/qt6/bin/qmltestrunner",
        "-input",
        str(directory / "tst_emoji_recorder.qml"),
        "-import",
        str(directory),
    ]
    result = subprocess.run(
        command,
        check=False,
        env=environment,
        capture_output=True,
        text=True,
        timeout=45,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    assert "ISOLATION_PASS" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output
    if mutation:
        expected = {
            "emoji": "test_emoji_filter_selection",
            "command": "test_recorder_commands_state",
            "collector": "test_discovery_collectors",
            "exit": "test_recorder_exit_collectors",
        }[mutation]
        assert (
            result.returncode != 0
            and f"FAIL!  : qmltestrunner::EmojiRecorderWarnings::{expected}" in output
        ), output
        print("NEGATIVE_CONTROL_DETECTED", mutation)
    else:
        assert result.returncode == 0 and "7 passed, 0 failed" in output, output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime", "lint-harness"))
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--mutation", choices=("emoji", "command", "collector", "exit"))
    args = parser.parse_args()
    if args.mutation and args.mode != "runtime":
        parser.error("--mutation requires runtime")
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-emoji-recorder-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation = load_helper("grid-list-warnings.test.py")
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory, args.inject_warning))
        if args.mode == "lint":
            lint(directory)
        else:
            runtime(directory, args.mutation)
