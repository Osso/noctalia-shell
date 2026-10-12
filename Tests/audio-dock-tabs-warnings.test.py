#!/usr/bin/env python3
"""Only AudioTab/DockTab: production controls, synthetic services, denied host state."""

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).absolute().parents[1]
TARGETS = [
    Path("Modules/Panels/Settings/Tabs") / (name + "Tab.qml")
    for name in ("Audio", "Dock")
]


def load_helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


ISOLATION = load_helper("audio-notification-settings-warnings.test.py")


def stage_behavior(directory):
    helper = load_helper("clock-settings-warnings.test.py")
    helper.stage_runtime(directory)
    (directory / "tst_clock.qml").unlink()
    write = helper.write_module
    singleton = helper.singleton
    write(
        directory,
        "qs.Tabs",
        {target.stem: (ROOT / target).read_text() for target in TARGETS},
    )
    write(
        directory,
        "Quickshell",
        {
            "ShellScreen": "import QtQuick\nQtObject { property string name; property string model; property int width; property int height }",
            "Quickshell": singleton("""
property ShellScreen laptop: ShellScreen { name: 'eDP-1'; model: 'Laptop'; width: 1920; height: 1080 }
property ShellScreen external: ShellScreen { name: 'DP-1'; model: 'External'; width: 2560; height: 1440 }
property var screens: [laptop, external]
"""),
        },
    )
    write(
        directory,
        "Quickshell.Services.Pipewire",
        {
            "PwNode": """import QtQuick
QtObject {
  property string id
  property string description
  component AudioState: QtObject { property real volume: 0.4; property bool muted: false }
  property AudioState audio: AudioState {}
}""",
        },
    )
    write(
        directory,
        "qs.Services.Compositor",
        {
            "CompositorService": singleton(
                "function getDisplayScale(name) { return name === 'DP-1' ? 1.5 : 1; }"
            ),
        },
    )
    write(
        directory,
        "qs.Services.Media",
        {
            "AudioService": """pragma Singleton
import QtQuick
import Quickshell.Services.Pipewire
QtObject {
  property PwNode speaker: PwNode { id: 'speaker'; description: 'Speakers' }
  property PwNode headphones: PwNode { id: 'headphones'; description: 'Headphones'; audio.volume: 0.7 }
  property PwNode microphone: PwNode { id: 'mic'; description: 'Microphone' }
  property PwNode headset: PwNode { id: 'headset'; description: 'Headset' }
  property var sinks: [speaker, headphones]
  property var sources: [microphone, headset]
  property PwNode sink: speaker
  property PwNode source: microphone
  property real volume: sink.audio.volume
  property bool muted: sink.audio.muted
  property real inputVolume: 0.3
  property bool inputMuted: false
  property bool isSwitchingSink: false
  property var volumeWrites: []
  function setVolume(value) { volumeWrites = volumeWrites.concat([value]); sink.audio.volume = value; }
  function setInputVolume(value) { inputVolume = value; }
  function setInputMuted(value) { inputMuted = value; }
  function setAudioSink(node) { sink = node; }
  function setAudioSource(node) { source = node; }
}""",
            "MediaService": singleton(
                "property int updates: 0\nfunction updateCurrentPlayer() { updates++; }"
            ),
        },
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["general"]["animationDisabled"] = True
    defaults["ui"].update(fontDefault="DejaVu Sans", fontFixed="DejaVu Sans Mono")
    defaults["audio"]["mprisBlacklist"] = ["FirstPlayer", "SecondPlayer"]
    defaults["dock"].update(enabled=True, monitors=["eDP-1"])
    declarations = []
    sections = []
    for section, values in defaults.items():
        if isinstance(values, dict):
            fields = []
            for key, value in values.items():
                kind = (
                    "bool"
                    if isinstance(value, bool)
                    else "real"
                    if isinstance(value, (int, float))
                    else "var"
                )
                fields.append(f"property {kind} {key}: {json.dumps(value)}")
            type_name = section[0].upper() + section[1:] + "State"
            declarations.append(
                f"component {type_name}: QtObject {{\n" + "\n".join(fields) + "\n}"
            )
            sections.append(f"property {type_name} {section}: {type_name} {{}}")
    declarations.append(
        "component SettingsState: QtObject {\n" + "\n".join(sections) + "\n}"
    )
    (directory / "qs/Commons/Settings.qml").write_text(
        singleton(
            "\n".join(declarations) + "\nproperty SettingsState data: SettingsState {}"
        )
    )
    (directory / "qs/Commons/I18n.qml").write_text(
        singleton("""
function tr(key, values) {
  if (key === 'system.monitor-description')
    return values.model + ':' + values.width + 'x' + values.height + '@' + values.scale;
  return key;
}
""")
    )
    harness = directory / "tst_audio_dock.qml"
    harness.write_text(
        (ROOT / "Tests/Qml/AudioDockTabsWarningsHarness.qml").read_text()
    )
    return harness


def run_sandboxed(mode, directory):
    mounts = Path("/proc/self/mountinfo").read_text()
    for path in ("/home", "/syncthing", "/run"):
        assert any(
            line.split()[4] == path and " - tmpfs " in line
            for line in mounts.splitlines()
        ), path
    environment = ISOLATION.isolated_environment(directory)
    if mode == "lint":
        load_helper("media-mini-warnings.test.py").stage_modules(directory)
        command = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            *[str(directory / "qs" / target) for target in TARGETS],
        ]
    else:
        harness = stage_behavior(directory)
        if mode == "lint-harness":
            command = [
                "/usr/lib/qt6/bin/qmllint",
                "--bare",
                "-I",
                str(directory),
                "-I",
                "/usr/lib/qt6/qml",
                "--max-warnings",
                "0",
                str(harness),
            ]
        else:
            command = [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(harness),
                "-import",
                str(directory),
            ]
    code, output = ISOLATION.run_child(command, directory, environment)
    (directory / f"{mode}.log").write_text(output)
    if mode == "lint":
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        for target in TARGETS:
            owned = [line for line in warnings if str(target) + ":" in line]
            counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in owned)
            print(
                target.name, "WARNINGS", dict(counts), "TOTAL", len(owned), flush=True
            )
        assert not warnings, output
    elif mode == "behavior":
        assert "0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
            output,
        ), output
    assert code == 0, code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior", "lint-harness"))
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    sys.addaudithook(ISOLATION.audit)
    with (
        patch("os.stat", ISOLATION.guard_metadata(os.stat)),
        patch("os.lstat", ISOLATION.guard_metadata(os.lstat)),
        patch("os.readlink", ISOLATION.guard_metadata(os.readlink)),
    ):
        ISOLATION.prove_denial()
        if args.sandbox:
            run_sandboxed(args.mode, args.sandbox)
            return
        with tempfile.TemporaryDirectory(
            prefix="noctalia-audio-dock-tabs-"
        ) as temporary:
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
            code, _ = ISOLATION.run_child(
                command,
                directory,
                {"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": temporary},
            )
            raise SystemExit(code)


if __name__ == "__main__":
    main()
