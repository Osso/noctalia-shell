# QML warning evidence

Verified: 2026-10-12. Documentation only; no new tests or live actions.

## Proof scope and revisions

Primary receipts: `/tmp/noctalia-verify-qml-final-static-iwc0jxxs/{REPORT.md,warning-inventory.json,installed-type-evidence.json}` (consumed completely). Exact static revision: `dba5edf36cddabdc914bfdd471f38b489a8e4a46`.

- Saved `./run-tests.sh qml`: exit 0, 158.154 seconds; 401 discovered/reached entries, zero skipped/excluded files. 302 default-context entries and 99 owner-staged entries; not 401 separate processes. Source/test/dispatcher preservation covers 758 hashes.
- Raw text: 102 warnings = 97 production + three wrong-context harness rows + two intentional negative controls; 187 infos, zero Error/Critical/Fatal headers. Owner JSON: 96 reports, 97 successful file results, zero warnings/errors and five unused-import infos. A locale advisory remains. Nothing was suppressed or discarded.
- Later `1a913964b` / `393b59f86` repair ToastScreen/TrayMenu fixture-context lint; reported exact owner proof is strict zero warnings, with a genuine semantic warning propagating native exit 255. `6832a536c` routes both through strict owners globally. These address the two ToastScreen read-only-data rows and one TrayMenu PanelService.panels row, not production diagnostics. **No new full 401-entry run after these revisions is claimed.**
- The original aggregate gate failed after 39 passing checks at `Tests/bar-action-helper-guards.test.js`. Subsequent partitioned proof is scoped evidence, not a green full runner. Individual feature/runtime boundaries remain in [testing](../specs/testing.md).
- User-approved live-DDC exclusion uses private representative data, preserving disabled DDC; [brightness host-probe scope](../specs/brightness.md#host-probe-coverage). Host-settings validation uses private fixtures only, not canonical-settings acceptance; [parent-runner evidence](../specs/testing.md#parent-test-config-guard-remediation-slices-ae). These behavioral coverage exclusions are not excluded static files. Real configuration, desktop surfaces and canonical runtime remain outside this report.

## Exact production inventory

97 rows across 35 files: **73 missing-property, 15 unresolved-type, five uncreatable-type, four incompatible-type; zero unqualified and zero block-scoped-var**. This is deduplicated text diagnostic scope, not interchangeable with per-context JSON counts. Exact messages, source positions, full warning blocks and installed-type references remain in `warning-inventory.json` above.

Table abbreviations: M = missing-property, R = unresolved-type, C = uncreatable-type, I = incompatible-type.

| Source | Rows | Categories |
|---|---:|---|
| `Commons/NColor.qml` | 1 | R1 |
| `Commons/Settings.qml` | 1 | M1 |
| `Commons/ShellState.qml` | 1 | R1 |
| `Modules/Bar/Extras/BarExclusionZone.qml` | 1 | C1 |
| `Modules/Bar/Extras/BarPill.qml` | 7 | M6 I1 |
| `Modules/Bar/Extras/BarWidgetLoader.qml` | 3 | M3 |
| `Modules/Bar/Extras/TrayMenu.qml` | 1 | M1 |
| `Modules/Bar/Widgets/Tray.qml` | 13 | M12 I1 |
| `Modules/Dock/Dock.qml` | 1 | M1 |
| `Modules/MainScreen/BarContentWindow.qml` | 5 | M4 C1 |
| `Modules/MainScreen/BarExclusionZone.qml` | 1 | C1 |
| `Modules/MainScreen/PopupMenuWindow.qml` | 1 | C1 |
| `Modules/MainScreen/SmartPanel.qml` | 4 | M4 |
| `Modules/Notification/Notification.qml` | 3 | M3 |
| `Modules/Panels/Bluetooth/BluetoothDevicesList.qml` | 1 | R1 |
| `Modules/Panels/Bluetooth/BluetoothPanel.qml` | 4 | M4 |
| `Modules/Panels/ControlCenter/ControlCenterWidgetLoader.qml` | 2 | M2 |
| `Modules/Panels/Launcher/Plugins/ApplicationsPlugin.qml` | 1 | R1 |
| `Modules/Panels/Launcher/Plugins/CalculatorPlugin.qml` | 2 | M2 |
| `Modules/Panels/Settings/Bar/BarWidgetSettingsDialog.qml` | 2 | M2 |
| `Modules/Panels/Settings/Bar/WidgetSettings/BatterySettings.qml` | 6 | M5 I1 |
| `Modules/Panels/Settings/ControlCenter/ControlCenterWidgetSettingsDialog.qml` | 2 | M2 |
| `Modules/Panels/Settings/Tabs/SessionMenuTab.qml` | 3 | M3 |
| `Modules/Panels/Tray/TrayDrawerPanel.qml` | 2 | M2 |
| `Modules/Startup/SettingsLoadError.qml` | 1 | C1 |
| `Modules/Toast/ToastScreen.qml` | 6 | M6 |
| `Modules/Tooltip/Tooltip.qml` | 1 | M1 |
| `Services/Compositor/CompositorService.qml` | 7 | M7 |
| `Services/Location/CalendarService.qml` | 1 | R1 |
| `Services/Location/LocationService.qml` | 1 | R1 |
| `Services/Networking/BluetoothService.qml` | 8 | R8 |
| `Services/Networking/NetworkService.qml` | 1 | I1 |
| `Services/System/HostService.qml` | 1 | M1 |
| `Services/UI/WallpaperService.qml` | 1 | R1 |
| `Widgets/NPopupContextMenu.qml` | 1 | M1 |

## Metadata versus interface blockers

Installed evidence links declarations to 96 of the 102 text rows; linkage is not proof that all 97 production rows are upstream bugs or runtime-safe.

- **Opaque/incomplete linkage:** core PopupAnchor declares `updateAnchor` at line 876, while `_Window` exposes an opaque PopupAnchor. Core UntypedObjectModel declares `values` at line 1637; other modules expose opaque declarations. `_Window` Anchors declares left/right/top/bottom at lines 17–20, unlike opaque declarations elsewhere. Io FileView names `FileViewAdapter` while its concrete component and JsonAdapter prototype use `qs::io::FileViewAdapter`. Bluetooth namespaced adapter/enums and PanelWindow creatability also require framework metadata/resolution investigation. Qt.application.font and DataStreamParser.text remain diagnostics, not established runtime contracts.
- **Heterogeneous contracts:** QObject/QQuickItem Loader items, optional widget screen/scaling/onLoaded, panel/dialog methods, Repeater children and selected compositor backends lack truthful shared static interfaces. Metadata presence elsewhere cannot supply these contracts. The inspected 40 registered widget types do not share all optional members; see [bar contract](../specs/bar.md#optional-dynamic-widget-loader-contract). QVariantMap→QVariantHash compatibility remains a separate type issue.
- **Remaining genuine blockers:** framework export/linkage and lifecycle work; truthful Loader/backend interfaces or narrowly justified type changes; unresolved map/hash compatibility. These require implementation/new approved scope, not warning suppression, fake shared APIs or excluded files.

Primary installed metadata below uses absolute paths and whole-file SHA-256 recorded in `installed-type-evidence.json`; that receipt retains all component declarations, line numbers and additional service-module hashes. Packages recorded there: quickshell 0.3.2-1, qt6-base 6.12.0-2, qt6-declarative 6.12.0-1. Auxiliary package query also emitted an unrelated missing-signature error; it is not QML proof.

| Metadata path | SHA-256 |
|---|---|
| `/usr/lib/qt6/qml/Quickshell/quickshell-core.qmltypes` | `aec65666b60e2f7973ed94b91cc61c1e9c96b36fe2978409a12fdfdb039cdbce` |
| `/usr/lib/qt6/qml/Quickshell/_Window/quickshell-window.qmltypes` | `0e6f53cac2a93833274b9ac9ba128e56f0b30ba63edc029334e140f710e4a9d7` |
| `/usr/lib/qt6/qml/Quickshell/Io/quickshell-io.qmltypes` | `3767e846b159cbd6bb547b908985389f4aa6b30463e8913da12b91390552cd9b` |
| `/usr/lib/qt6/qml/Quickshell/Bluetooth/quickshell-bluetooth.qmltypes` | `7fd2819dde1b5a5cbd461155c8614521044082eaf9c8951831647e95ba4ae40b` |
| `/usr/lib/qt6/qml/builtins.qmltypes` and `/usr/lib/qt6/qml/QML/plugins.qmltypes` | `156e5981000f67e9521aa38bc05cc2cc2ff10f7c7205e54907855b94ae0a83c1` |
| `/usr/lib/qt6/qml/QtQuick/plugins.qmltypes` | `8c57e13edb49e3c6f86df80c8c78f877bec44823ed6dcc64752e272f3e11326e` |

## Runtime residuals are separate

- **ActiveWindow:** `/tmp/noctalia-active-window-reload-diagnosis/proof.md` and native logs, revision `e24cf960ff72308f9769242b0df40990bcbb83fb`, reproduce four undefined-assignment warnings per old-generation destruction: four loads, 16 warnings across three reloads plus shutdown (RED exit 1). Native tracing places QJSEngine interruption before Repeater teardown. A private debugger control changing only interruption true→false yields zero warnings with identical settled 145×25 dimensions (exit 0); live-engine destruction also yields zero. Neither is a shipped fix nor evidence that disabling interruption is safe. No safe public pre-reload hook is available in the investigated lifecycle. Framework generation lifecycle or newly approved teardown-order scope is required; startup settings/data is not the reproduced cause.
- **Sound:** nine raw expected isolated backend/error-fixture warnings remain; the removed injected-parameter deprecation does not establish warning-free audio. Contract and natural end-of-media gap: [sound-service](../specs/sound-service.md#tests-asserting-this-spec).
- **Private Niri:** private-compositor startup transport diagnostics are distinct from the tested client’s zero-warning result. Do not attribute compositor startup warnings to client acceptance or infer whole-desktop cleanliness. Native protocol/client boundaries: [compositor](../specs/compositor.md), [scoped integration evidence](../specs/testing.md#popup-window-isolated-runtime).

No new full runner, live settings, canonical restart, hardware, desktop or deployment acceptance is asserted. Temporary receipts are local evidence artifacts, not tracked fixtures; this grouped inventory preserves their production counts in the repository.
