#!/usr/bin/env python3
"""One-file lint and offscreen production Wi-Fi list with inert IO boundaries."""

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
TARGET = Path("Modules/Panels/WiFi/WiFiNetworksList.qml")
GOLDEN = ROOT / "Tests/fixtures/wifi-networks-list-geometry.json"


def load_staging():
    spec = importlib.util.spec_from_file_location(
        "wifi_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    load_staging().stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("WIFI_LIST_LINT_COUNTS", dict(counts))
    assert not counts, dict(counts)
    assert result.returncode == 0, result.returncode


def singleton(directory, name, body):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"
    )


def stage_list(directory):
    for relative in [TARGET] + [
        Path(f"Widgets/{name}.qml")
        for name in (
            "NBox",
            "NText",
            "NIcon",
            "NButton",
            "NIconButton",
            "NBusyIndicator",
        )
    ]:
        destination = directory / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    commons = directory / "Commons"
    singleton(
        commons,
        "Settings",
        'readonly property var data: ({ui: {fontDefault: "Sans Serif", fontFixed: "monospace", fontDefaultScale: 1, fontFixedScale: 1}})',
    )
    style = {
        "uiScaleRatio": 1,
        "marginXXS": 2,
        "marginXS": 4,
        "marginS": 6,
        "marginM": 8,
        "marginL": 12,
        "radiusXS": 2,
        "radiusS": 4,
        "radiusM": 8,
        "radiusL": 12,
        "borderS": 1,
        "borderL": 2,
        "fontSizeXXS": 8,
        "fontSizeXS": 9,
        "fontSizeS": 10,
        "fontSizeM": 12,
        "fontSizeL": 14,
        "fontSizeXXL": 20,
        "fontWeightMedium": 500,
        "fontWeightBold": 700,
        "baseWidgetSize": 32,
        "animationFast": 0,
        "animationNormal": 0,
        "animationSlow": 100,
        "opacityFull": 1,
        "opacityMedium": 0.6,
    }
    singleton(
        commons,
        "Style",
        "\n".join(
            f"readonly property real {key}: {value}" for key, value in style.items()
        ),
    )
    colors = {
        "mPrimary": "#3355aa",
        "mSecondary": "#557733",
        "mError": "#cc2233",
        "mSurface": "#202020",
        "mSurfaceVariant": "#141414",
        "mOnSurface": "#ffffff",
        "mOnSurfaceVariant": "#aaaaaa",
        "mOutline": "#808080",
        "mHover": "#404040",
        "mOnPrimary": "#ffffff",
        "mOnHover": "#ffffff",
        "transparent": "transparent",
    }
    singleton(
        commons,
        "NColor",
        "\n".join(
            f'readonly property color {key}: "{value}"' for key, value in colors.items()
        ),
    )
    singleton(
        commons,
        "Icons",
        'readonly property string defaultIcon: "wifi"\nreadonly property string fontFamily: "Sans Serif"\nfunction get(icon) { return "*"; }',
    )
    singleton(
        commons,
        "Logger",
        'function w(...args) { console.warn(...args); }\nfunction callStack() { throw new Error("Unexpected icon"); }',
    )
    singleton(
        commons,
        "I18n",
        """property bool translated: false
function tr(key, args) {
  if (key === "system.signal-strength") return args.signal + "%";
  const labels = {
    "wifi.panel.connected": ["Connected", "Connexion établie"],
    "wifi.panel.disconnecting": ["Disconnecting", "Déconnexion en cours"],
    "wifi.panel.forgetting": ["Forgetting", "Suppression en cours"],
    "wifi.panel.saved": ["Saved", "Réseau enregistré"],
    "wifi.panel.connect": ["Connect", "Se connecter"],
    "wifi.panel.disconnect": ["Disconnect", "Se déconnecter"],
    "wifi.panel.password": ["Password", "Mot de passe"],
    "wifi.panel.enter-password": ["Enter password", "Saisir le mot de passe"],
    "wifi.panel.forget-network": ["Forget network?", "Oublier ce réseau ?"],
    "wifi.panel.forget": ["Forget", "Oublier"]
  };
  return labels[key] ? labels[key][translated ? 1 : 0] : key;
}""",
    )
    singleton(
        directory / "Services/UI",
        "TooltipService",
        "function show(...args) {}\nfunction hide() {}",
    )
    singleton(
        directory / "Services/Networking",
        "NetworkService",
        """property string connectingTo: ""
property string disconnectingFrom: ""
property string forgettingNetwork: ""
property bool connecting: false
property var requests: []
function isSecured(security) { return security === "WPA2"; }
function signalIcon(signal, connected) { return connected ? "wifi" : "wifi-low"; }
function connect(ssid) { requests = requests.concat([{action: "connect", ssid: ssid}]); }
function disconnect(ssid) { requests = requests.concat([{action: "disconnect", ssid: ssid}]); }""",
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/WiFiNetworksListWarningsHarness.qml",
        directory / "tst_wifi.qml",
    )


def isolated_environment(directory):
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
    for name in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / name
        path.mkdir(mode=0o700)
        environment[name] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/wifi-test-session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/wifi-test-system",
    )
    return environment


def behavior(directory, snapshot, baseline):
    stage_list(directory)
    result = subprocess.run(
        ["quickshell", "--no-color", "-p", str(directory / "tst_wifi.qml")],
        cwd=ROOT,
        env=isolated_environment(directory),
        capture_output=True,
        text=True,
        timeout=45,
    )
    output = result.stdout + result.stderr
    print(
        "\n".join(line for line in output.splitlines() if "WIFI_SNAPSHOT " not in line)
    )
    assert result.returncode == 0, "Offscreen production list failed"
    assert "WIFI_LIST_BEHAVIOR_PASS" in output, output
    assert not re.search(r"\b(?:WARN|ERROR|FATAL)\b", output), output
    records = [
        json.loads(record)
        for record in re.findall(r"WIFI_SNAPSHOT (\{[^\n]+\})", output)
    ]
    assert len(records) == 4, len(records)
    if snapshot is not None:
        snapshot.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
    if not baseline:
        assert records == json.loads(GOLDEN.read_text()), (
            "Geometry/content differs from pre-fix production baseline"
        )
    print("WIFI_LIST_BEHAVIOR_PASS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    if args.mode == "behavior" and args.baseline and not args.snapshot:
        parser.error("--baseline requires --snapshot")
    settings = Path("/home/osso/.config/noctalia/settings.json")
    original = settings.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    with tempfile.TemporaryDirectory(prefix="noctalia-wifi-list-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        backup = directory / "settings-backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
        try:
            if args.mode == "lint":
                lint(directory)
            else:
                behavior(directory, args.snapshot, args.baseline)
        finally:
            assert hashlib.sha256(settings.read_bytes()).hexdigest() == digest, (
                "Real settings changed"
            )
            print("SETTINGS_SHA_UNCHANGED", digest)


if __name__ == "__main__":
    main()
