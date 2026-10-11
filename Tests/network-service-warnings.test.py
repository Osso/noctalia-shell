#!/usr/bin/env python3
"""Targeted NetworkService lint and real offscreen Process/FileView regression.

Only command providers and neighboring services are fixtures. Quickshell I/O,
production NetworkService, callback ordering and JSON persistence remain real.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SERVICE = Path("Services/Networking/NetworkService.qml")
FIXTURE = ROOT / "Tests/network-service"


def lint(directory):
    spec = importlib.util.spec_from_file_location(
        "media_lint", ROOT / "Tests/media-mini-warnings.test.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / SERVICE),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "lint.log").write_text(output)
    print(output, end="")
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("NETWORK_LINT_COUNTS", dict(counts))
    # Installed Process.environment metadata expects QVariantHash, not the JS map.
    assert dict(counts) == {"incompatible-type": 1}, dict(counts)
    assert result.returncode == 255, result.returncode


def write_module(directory, relative, sources):
    path = directory / relative
    path.mkdir(parents=True, exist_ok=True)
    (path / "qmldir").write_text(
        "".join(f"singleton {name} 1.0 {name}.qml\n" for name in sources)
    )
    for name, body in sources.items():
        (path / f"{name}.qml").write_text(body)


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def stage_runtime(directory, mode):
    for name in ("home", "config", "cache", "data", "state", "runtime", "bin"):
        (directory / name).mkdir(mode=0o700)
    write_module(
        directory,
        "Commons",
        {
            "Settings": singleton(
                f"property string cacheDir: {json.dumps(str(directory / 'cache') + '/')}\n"
                "property QtObject data: QtObject {\n"
                "  property QtObject network: QtObject { property bool wifiEnabled: false }\n}"
            ),
            "Logger": singleton("""property var warnings: []
function i(...args) {}
function d(...args) {}
function w(...args) { warnings = warnings.concat([args.join(" ")]); }"""),
            "I18n": singleton("function tr(key, args) { return key; }"),
        },
    )
    write_module(
        directory,
        "Services/UI",
        {
            "ToastService": singleton("""property var notices: []
function showNotice(...args) { notices = notices.concat([args]); }
function showWarning(...args) { notices = notices.concat([args]); }"""),
        },
    )
    write_module(
        directory,
        "Services/Networking",
        {
            "NetworkService": (ROOT / SERVICE).read_text(),
            "BluetoothService": singleton("property bool airplaneModeToggled: false"),
        },
    )
    shutil.copyfile(FIXTURE / "shell.qml", directory / "shell.qml")
    for name in ("nmcli", "bash"):
        shutil.copyfile(FIXTURE / "provider.py", directory / "bin" / name)
        (directory / "bin" / name).chmod(0o700)
    cache = directory / "cache/network.json"
    if mode == "malformed":
        cache.write_text("{broken JSON")
    elif mode != "missing":
        cache.write_text(
            json.dumps(
                {
                    "knownNetworks": {
                        "Saved": {"profileName": "Saved", "lastConnected": 123}
                    },
                    "lastConnected": "Saved",
                }
            )
        )
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "QS_", "NOCTALIA_"))
        and key
        not in (
            "HOME",
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "DBUS_SYSTEM_BUS_ADDRESS",
            "NIRI_SOCKET",
            "SWAYSOCK",
            "HYPRLAND_INSTANCE_SIGNATURE",
        )
    }
    environment.update(
        HOME=str(directory / "home"),
        XDG_CONFIG_HOME=str(directory / "config"),
        XDG_CACHE_HOME=str(directory / "cache"),
        XDG_DATA_HOME=str(directory / "data"),
        XDG_STATE_HOME=str(directory / "state"),
        XDG_RUNTIME_DIR=str(directory / "runtime"),
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent",
        PATH=str(directory / "bin"),
        NETWORK_FIXTURE_DIR=str(directory),
        NETWORK_FIXTURE_MODE=mode,
    )
    return environment


def run_case(directory, mode):
    directory.mkdir(mode=0o700)
    environment = stage_runtime(directory, mode)
    # Keep the Quickshell IPC socket below the Unix-domain path length limit.
    with tempfile.TemporaryDirectory(prefix="nnr-") as runtime:
        environment["XDG_RUNTIME_DIR"] = runtime
        exit_code = run_shell(directory, environment)
    log = (directory / "runtime.log").read_text()
    print(mode, log, end="")
    assert exit_code == 0 and "NETWORK_PASS" in log, log
    assert not re.search(
        r"ReferenceError|TypeError|Binding loop|NETWORK_FAIL|ERROR", log
    ), log
    calls = [
        json.loads(line)
        for line in (directory / "requests.jsonl").read_text().splitlines()
    ]
    startup = [
        ["radio", "wifi"],
        ["-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"],
        ["networking", "connectivity", "check"],
    ]
    assert sorted(calls[:3]) == sorted(startup), calls
    assert not any(call[:2] == ["radio", "wifi"] and len(call) > 2 for call in calls), (
        calls
    )
    if mode in ("profile-error", "scan-error"):
        scans = [call for call in calls if "SSID,SECURITY,SIGNAL,IN-USE" in call]
        assert len(scans) == (0 if mode == "profile-error" else 1), calls
        assert not any(call[:2] == ["connection", "up"] for call in calls), calls
        return
    cache = json.loads((directory / "cache/network.json").read_text())
    assert cache["lastConnected"] == "", cache
    assert set(cache["knownNetworks"]) == {"Saved"}, cache
    assert cache["knownNetworks"]["Saved"]["lastConnected"] > 123, cache
    assert ["connection", "up", "id", "Saved"] in calls, calls
    assert [
        "device",
        "wifi",
        "connect",
        "New",
        "password",
        "fixture-secret",
    ] in calls, calls
    assert ["device", "wifi", "connect", "Denied"] in calls, calls


def run_shell(directory, environment):
    with (directory / "runtime.log").open("w") as output:
        process = subprocess.Popen(
            ["/usr/bin/quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            env=environment,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            process.wait(timeout=20)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
    return process.returncode


def behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    try:
        for mode in ("valid", "missing", "malformed", "profile-error", "scan-error"):
            run_case(directory / mode, mode)
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        assert backup.read_bytes() == original, "backup changed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    if args.artifacts:
        args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
        globals()[args.mode](args.artifacts.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="noctalia-network-") as temporary:
            globals()[args.mode](Path(temporary))


if __name__ == "__main__":
    main()
