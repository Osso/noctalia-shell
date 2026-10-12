#!/usr/bin/env python3
"""Run actual SoundService/MediaPlayer without host audio, desktop or settings.

Bubblewrap hides host homes, /run sockets and /dev devices and unshares network.
Missing media exercises real asynchronous errors, not audio playback. Stopped-state
signals additionally exercise one-shot/repeat cleanup without decoding valid audio.
"""

from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def stage_service(directory):
    services = directory / "Services/System"
    commons = directory / "Commons"
    services.mkdir(parents=True)
    commons.mkdir()
    shutil.copyfile(
        ROOT / "Services/System/SoundService.qml", services / "SoundService.qml"
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/SoundServiceHarness.qml",
        directory / "SoundServiceHarness.qml",
    )
    (directory / "shell.qml").write_text(
        "import qs.Commons\nSoundServiceHarness { logger: Logger }\n"
    )
    (commons / "Logger.qml").write_text(
        """pragma Singleton
import QtQuick
QtObject {
  property var observe
  property var observeError
  function i() {}
  function d(service, message, path) {
    if (message === "Playing sound:") observe(path);
  }
  function w(service, message, path) {
    if (message === "Error playing sound:") observeError(path);
    else throw new Error("Unexpected service warning: " + message);
  }
}
"""
    )


def sandbox_command(directory):
    command = [
        "bwrap",
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--ro-bind",
        "/",
        "/",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/run",
        "--tmpfs",
        "/tmp",
        "--tmpfs",
        "/home",
        "--tmpfs",
        "/syncthing",
        "--bind",
        str(directory),
        str(directory),
        "--clearenv",
    ]
    environment = {
        "PATH": "/usr/bin",
        "LANG": "C.UTF-8",
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "QT_MEDIA_BACKEND": "ffmpeg",
    }
    for variable, name in {
        "HOME": "home",
        "XDG_CONFIG_HOME": "config",
        "XDG_CACHE_HOME": "cache",
        "XDG_DATA_HOME": "data",
        "XDG_STATE_HOME": "state",
        "XDG_RUNTIME_DIR": "runtime",
        "NOCTALIA_CONFIG_DIR": "noctalia-config",
        "NOCTALIA_CACHE_DIR": "noctalia-cache",
    }.items():
        path = directory / name
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    for variable, value in environment.items():
        command.extend(["--setenv", variable, value])
    command.extend(
        [
            "--chdir",
            str(directory),
            "quickshell",
            "--no-color",
            "-p",
            str(directory / "shell.qml"),
        ]
    )
    return command


def main():
    with tempfile.TemporaryDirectory(prefix="noctalia-sound-runtime-") as temporary:
        directory = Path(temporary)
        stage_service(directory)
        command = sandbox_command(directory)
        settings = directory / "home/.config/noctalia/settings.json"
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
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=15,
            )
        finally:
            assert settings.read_bytes() == original, "fixture settings changed"
            assert backup.read_bytes() == original, "fixture backup changed"
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, f"SoundService runtime exit {result.returncode}"
        assert (
            "SOUND_SERVICE_PASS:" in output and "SOUND_SERVICE_FAIL:" not in output
        ), output
        # Expected backend errors come from intentionally absent files. QML
        # context/reference failures are not part of that fixture contract.
        for diagnostic in (
            "ReferenceError",
            "TypeError",
            "Error:",
            "Unable to assign",
            "Failed to load configuration",
        ):
            assert diagnostic not in output, output


if __name__ == "__main__":
    main()
