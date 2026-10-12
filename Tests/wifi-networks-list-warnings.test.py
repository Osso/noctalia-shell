#!/usr/bin/env python3
"""One-file lint and offscreen production Wi-Fi list with inert IO boundaries."""

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
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


def audited_fixture():
    spec = importlib.util.spec_from_file_location(
        "wifi_panel_fixture", ROOT / "Tests/wifi-panel-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    load_staging().stage_modules(directory)
    code, output = audited_fixture().run_audited(
        directory,
        isolated_environment(directory),
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        "list-lint",
    )
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("WIFI_LIST_LINT_COUNTS", dict(counts))
    assert not counts, dict(counts)
    assert code == 0, code


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
function connect(ssid, password) {
  const request = {action: "connect", ssid: ssid};
  if (password !== undefined) request.password = password;
  requests = requests.concat([request]);
}
function disconnect(ssid) { requests = requests.concat([{action: "disconnect", ssid: ssid}]); }""",
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/WiFiNetworksListWarningsHarness.qml",
        directory / "tst_wifi.qml",
    )


def stage_harness(directory):
    stage_list(directory)
    for relative in (
        "Commons",
        "Widgets",
        "Services/UI",
        "Services/Networking",
        "Modules/Panels/WiFi",
    ):
        module = directory / relative
        entries = ["module qs." + relative.replace("/", ".")]
        for source in sorted(module.glob("*.qml")):
            prefix = (
                "singleton "
                if source.read_text().startswith("pragma Singleton")
                else ""
            )
            entries.append(f"{prefix}{source.stem} 1.0 {source.name}")
        (module / "qmldir").write_text("\n".join(entries) + "\n")
    (directory / "qs").symlink_to(".", target_is_directory=True)


def check_harness(directory, environment, label):
    code, output = audited_fixture().run_audited(
        directory,
        environment,
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
            str(directory / "tst_wifi.qml"),
        ],
        label,
    )
    diagnostics = [
        diagnostic
        for file in json.loads(output)["files"]
        for diagnostic in file["warnings"]
        if diagnostic["type"] in ("warning", "error")
    ]
    counts = Counter(diagnostic["id"] for diagnostic in diagnostics)
    print("WIFI_LIST_HARNESS_LINT_COUNTS", dict(counts), "EXIT", code)
    return code, diagnostics


def lint_harness(directory):
    environment = isolated_environment(directory)
    stage_harness(directory)
    code, diagnostics = check_harness(directory, environment, "harness-lint")
    assert code == 0 and not diagnostics, (code, diagnostics)
    return environment


def lint_harness_regression(directory):
    environment = lint_harness(directory)
    harness = directory / "tst_wifi.qml"
    source = harness.read_text()
    marker = "id: harness"
    assert source.count(marker) == 1, "injection owner must be unique"
    harness.write_text(
        source.replace(
            marker,
            marker + "\n  property int injectedWarning: harness.missingLintProbe",
            1,
        )
    )
    code, diagnostics = check_harness(directory, environment, "harness-injected")
    assert code != 0, "injected diagnostic was accepted"
    assert any(
        diagnostic["id"] == "missing-property"
        and "missingLintProbe" in diagnostic["message"]
        for diagnostic in diagnostics
    ), diagnostics
    print("WIFI_LIST_HARNESS_WARNING_REJECTED")


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


PASSWORD_MUTATIONS = {
    "submit-signal": (
        "root.passwordSubmitted(networkItem.networkSsid, password);",
        "",
        "submission clears credentials and closes editor",
    ),
    "cancel-signal": (
        "root.passwordCancelled();",
        "",
        "cancel clears credentials and closes editor",
    ),
    "submit-reset": (
        'function submitPassword(password) {\n          pwdInput.text = "";',
        "function submitPassword(password) {",
        "submission must clear editor before signal",
    ),
    "cancel-reset": (
        'function cancelPassword() {\n          pwdInput.text = "";',
        "function cancelPassword() {",
        "cancellation must clear editor before signal",
    ),
    "submit-password": (
        "root.passwordSubmitted(networkItem.networkSsid, password);",
        'root.passwordSubmitted(networkItem.networkSsid, "");',
        "submission signal must preserve SSID/password",
    ),
    "busy-enter": (
        "if (text && !NetworkService.connecting) {",
        "if (text) {",
        "rejected Enter must not emit submission",
    ),
    "empty-enter": (
        "if (text && !NetworkService.connecting) {",
        "if (!NetworkService.connecting) {",
        "rejected Enter must not emit submission",
    ),
    "submit-owner": (
        "onClicked: networkItem.submitPassword(pwdInput.text)",
        "onClicked: submitPassword(pwdInput.text)",
        "shadow owner handled submission",
    ),
    "cancel-owner": (
        "onClicked: networkItem.cancelPassword()",
        "onClicked: cancelPassword()",
        "shadow owner handled cancellation",
    ),
}


def stage_password_probe(directory, owner_shadow, mutation):
    source_path = directory / TARGET
    source = source_path.read_text()
    if owner_shadow:
        for marker, shadow in (
            (
                "id: pwdInput",
                'property string networkSsid: "shadow-editor"',
            ),
            (
                'text: I18n.tr("wifi.panel.connect")\n                fontSize: Style.fontSizeXXS',
                'function submitPassword(password) { throw new Error("shadow owner handled submission"); }',
            ),
            (
                "onClicked: networkItem.cancelPassword()",
                'function cancelPassword() { throw new Error("shadow owner handled cancellation"); }',
            ),
        ):
            assert source.count(marker) == 1, marker
            source = source.replace(marker, marker + "\n                " + shadow, 1)
    if mutation:
        original, replacement, _ = PASSWORD_MUTATIONS[mutation]
        assert source.count(original) == 1, (mutation, original)
        source = source.replace(original, replacement, 1)
    source_path.write_text(source)


def behavior(directory, snapshot, baseline, owner_shadow=False, mutation=None):
    environment = isolated_environment(directory)
    stage_harness(directory)
    stage_password_probe(directory, owner_shadow, mutation)
    code, output = audited_fixture().run_audited(
        directory,
        environment,
        ["/usr/bin/quickshell", "--no-color", "-p", str(directory / "tst_wifi.qml")],
        "behavior",
    )
    print(
        "\n".join(line for line in output.splitlines() if "WIFI_SNAPSHOT " not in line)
    )
    if mutation:
        expected = PASSWORD_MUTATIONS[mutation][2]
        assert code != 0 and "WIFI_LIST_FAIL" in output and expected in output, (
            mutation,
            code,
            output,
        )
        print("WIFI_PASSWORD_MUTATION_REJECTED", mutation)
        return
    assert code == 0, "Offscreen production list failed"
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
    parser.add_argument(
        "mode", choices=("lint", "behavior", "lint-harness", "lint-harness-regression")
    )
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--owner-shadow", action="store_true")
    parser.add_argument("--mutation", choices=PASSWORD_MUTATIONS)
    args = parser.parse_args()
    if args.mutation and (args.mode != "behavior" or not args.owner_shadow):
        parser.error("--mutation requires behavior --owner-shadow")
    if args.mode == "behavior" and args.baseline and not args.snapshot:
        parser.error("--baseline requires --snapshot")
    with tempfile.TemporaryDirectory(prefix="noctalia-wifi-list-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation = audited_fixture().isolation
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        if args.mode == "behavior":
            behavior(
                directory,
                args.snapshot,
                args.baseline,
                args.owner_shadow,
                args.mutation,
            )
        else:
            globals()[args.mode.replace("-", "_")](directory)


if __name__ == "__main__":
    main()
