Network covers Wi-Fi radio state, scan scheduling, NetworkManager connection commands, cached known networks, connection status updates, and Wi-Fi icon/security helpers. Runtime source lives mainly in `Services/Networking/NetworkService.qml`.

## What it must do

### Cache, Wi-Fi state, and idle polling

- [x] Cache saves are debounced.
- [x] Wi-Fi state sync queries the live radio state.
- [x] On-demand network status refresh queries Ethernet, connected Wi-Fi, and connectivity state.
- [x] Setting Wi-Fi enabled updates settings first and starts the nmcli radio command.
- [x] Startup does not perform a background Wi-Fi scan.
- [x] Idle Ethernet/connectivity timers run only while an active network UI consumer is open.
- [x] Wi-Fi panel opening starts active polling and Wi-Fi scanning through NetworkService.
- [x] Wi-Fi panel closing releases active polling.
- [x] Delayed scan timers do not rescan while idle.

### Wi-Fi panel UI

- [x] Panel separates connected, existing, and cached networks from unsaved available networks, sorting each group by signal strength with connected networks first.
- [x] Disabled Wi-Fi shows an enable prompt; the panel distinguishes initial scanning from a confirmed empty result and supports manual refresh.
- [x] Saved and open networks connect directly; secured unknown networks prompt for a password.
- [x] Password entry supports submit, cancel, and Enter actions without retaining the typed password in persistent panel state.
- [x] Connected networks expose disconnect; saved networks expose forget confirmation; active targets show busy state and suppress duplicate actions.

### Scanning

- [x] Scan no-ops while Wi-Fi is disabled.
- [x] Scan queues a pending rescan and ignores superseded successful output instead of racing an active scan.
- [x] Scan resets stale errors and scan state before launching.
- [x] Scan refreshes known profiles before scanning networks.
- [x] nmcli scan output parsing handles SSIDs with colons, duplicate SSIDs, open networks, malformed rows, known-profile flags, cached-network flags, and last-connected cache updates.
- [x] Profile-query and Wi-Fi scan collectors buffer stdout/stderr and apply normal scan state from process-exit handlers after the exit status is known.
- [x] Nonzero exits from started profile-query or Wi-Fi scan processes clear busy state and publish a concrete error; queued rescans get a 100 ms follow-up, while delayed retry execution remains gated by an active Wi-Fi UI consumer.

### Connect, disconnect, and forget

- [x] Connect rejects empty or overlapping requests using both service and process state.
- [x] Connect sets busy state, target SSID, clears stale errors, resets process buffers, and advances operation identity.
- [x] Connect reuses existing or cached profiles without retaining typed passwords.
- [x] Connect creates new profiles with supplied passwords when no existing profile is known.
- [x] Disconnect rejects empty/overlapping requests, tracks the target SSID, resets process buffers, advances operation identity, and starts the disconnect process.
- [x] Connect/disconnect completion is exit-code-driven, identity-safe, and independent of localized stdout text.
- [x] Successful actions update status/cache as applicable, clear credentials/busy/error state, show notice, refresh status, and schedule scans only while polling.
- [x] Nonzero and failed-start actions preserve network/cache state, clear credentials/busy state, expose stderr/stdout diagnostics or a concrete fallback, and do not schedule scans that erase errors.
- [x] Forget rejects empty/overlapping requests, tracks the target SSID, resets buffered process state, and starts system profile deletion without mutating cache/UI state first.
- [x] The forget helper lists unescaped NetworkManager profile names, matches exact, `Auto `, and arbitrary numeric-suffix variants, and propagates list/delete failures.
- [x] Successful forget completion identity-checks the SSID, removes only that cached network, clears `lastConnected` when needed, updates known/existing UI state, persists cache changes, and schedules verification scan while polling.
- [x] Nonzero and failed-to-start forget operations preserve cache/UI state, clear busy state, expose a concrete error, and cannot let stale completion overwrite a newer request.

### Status and icons

- [x] Connection status updates disconnect other active networks.
- [x] Existing connected targets become connected, existing, and cached.
- [x] Missing connected targets are synthesized with placeholder security and full signal.
- [x] Missing disconnected targets are not synthesized.
- [x] Status updates force a `networks` property-change notification.
- [x] Passive device status synthesizes connected Wi-Fi networks from `nmcli device` output so bar icons do not require a background scan.
- [x] Passive device status clears stale connected Wi-Fi state when no Wi-Fi device is connected.
- [x] Ethernet and Wi-Fi radio status mutate state only after successful process exit; nonzero and failed-start checks preserve the last known state and log a concrete diagnostic.
- [x] Unknown or missing connectivity checks default connected Wi-Fi to the normal Wi-Fi icon instead of `world-off`.
- [x] Connected offline networks show the `world-off` icon only after a known offline/captive connectivity result.
- [x] `none` transitions immediately clear internet connectivity; `full` transitions restore it.
- [x] Repeated limited/portal results launch at most one fallback ping, expose offline state while validation is pending, and ignore ping completion superseded by a newer connectivity result.
- [x] Fallback ping failure remains offline, resets failure accumulation, reports the limitation, and scans only while active polling is retained.
- [x] Signal strength maps strong, medium, weak, and very weak/missing signal to the expected Wi-Fi icons.
- [x] Security helper rejects missing, placeholder, and blank security values.

### Wi-Fi panel actions

- [x] Saved and open networks connect directly; unsecured unsaved networks do not request credentials.
- [x] Secured unsaved networks open password entry, protect typed text, reject empty/overlapping submissions, and clear the editor whenever it hides, submits, or cancels.
- [x] Forget is offered only for saved disconnected networks and requires explicit confirmation before calling the service.
- [x] Known and available network lists route password and forget state through the panel consistently.

## Implementation inventory

- `Services/Networking/NetworkService.qml` - Wi-Fi radio state, scanning, connection commands, cache state, status updates, and icon/security helpers.
- `Modules/Panels/WiFi/WiFiPanel.qml` - Wi-Fi panel shell.
- `Modules/Panels/WiFi/WiFiNetworksList.qml` - network list, connect/disconnect/forget UI.
- `Modules/Panels/Settings/Tabs/NetworkTab.qml` - settings toggles for network features.
- `Modules/Bar/Widgets/WiFi.qml` - bar Wi-Fi/network status widget.

## Tests asserting this spec

- `Tests/qml-static-network-fixture.test.py` — isolated network harness is lint-clean and counted once; injected genuine warnings fail the static checker.
- `Tests/weather-wifi-workspace-isolation.test.py` — WiFi-list behavior/lint entrypoints deny host config and reject private settings/backup mutations.

- `Tests/bar-status-warnings.test.py behavior` adds two production WiFi bar-widget cases at `c14da3540`: fixture SSID/signal, Ethernet precedence/connectivity, disconnected tooltip, vertical pill collapse/geometry, panel/menu anchoring, WiFi enable/disable requests, settings dispatch, and inert wheel. Signals/icons come from an inert NetworkService; no NetworkManager/radio action, native input, real popup, or persistence is proved. Cohort lint and isolation: [testing](testing.md#bar-status-cohort).

- `Tests/network-forget-profiles.test.sh`
- `Tests/network-service-guards.test.js` — 24 mixed source-guard and extracted-function cases; not 24 live integration cases.
- `Tests/network-service-warnings.test.py` — standalone `lint` and `behavior`, optionally with `--artifacts <new-directory>`. After `e5f142928`, `c7f9d8315`, and `0444b1a4f`, adapter-boundary `unqualified` warnings drop 5→0; lint expects exactly one unsuppressed `incompatible-type` warning (Process.environment QVariantMap→QVariantHash) and exit status zero. Five offscreen cases (`valid`, `missing`, `malformed`, `profile-error`, `scan-error`) run actual NetworkService with real Quickshell Process/streams/FileView/JsonAdapter and private command providers. They cover startup status, loaded/reset cache, scan ordering, saved/new/denied connections, forget state, debounced JSON persistence, and profile/scan stderr failures preserving prior state. Providers maintain connected SSID across requests; no live NetworkManager mutation occurs. Isolation, acceptance, and remaining limits: [testing](testing.md#network-private-runtime).
- `Tests/simple-service-warnings.test.py` / `Tests/Qml/SimpleServiceHarness.qml` — production status/scan success and profile-query error ordering, radio recheck, and real delayed-scan timer execution while active versus suppression after polling ends. Commands and I/O are fake, not NetworkManager integration. Exact residual diagnostics and cohort proof: [testing](testing.md#simple-service-cohort).
- `Tests/wifi-panel-ui-guards.test.js` - runs the production-list behavioral harness; its panel signal routing checks remain source guards. Actual panel routing is separately exercised below.
- `Tests/wifi-panel-warnings.test.py` / `Tests/Qml/WiFiPanelWarningsHarness.qml` — at `2fdc52c90`, WiFiPanel-only lint drops 27→0. Actual panel and network lists exercise saved/open connect, disconnect, secured password submit/cancel/clearing, forget confirm/cancel, radio toggle requests, refresh/scan-again, error dismissal, list ordering, polling balance, and close/reopen Loader recreation with inert networking. These are direct signal calls, not physical input or live radio/backend authorization. Standalone modes and isolation: [testing](testing.md#wifi-panel-isolated-runtime).
- `Tests/wifi-networks-list-warnings.test.py` - standalone lint requires zero qmllint warnings and exit status zero. `behavior` runs standalone and directly in `run-tests.sh`'s `deterministic-unit` gate after battery-widget coverage; the discovered JavaScript suite also invokes it. `--snapshot <path>` optionally exports records without changing fixture comparison; `--baseline` requires a snapshot path and skips comparison. Offscreen behavior checks ordered delegate connect/disconnect requests, secured-network password request/submission/cancellation/clearing, forget confirmation/cancellation signals, busy states, and model replacement/reordering. Through `555b7f64c`/`d0b621346`, reported proof covers four scenarios and 28 exact geometry/content snapshots (seven states at widths 900/430 with normal/translated labels) against the pre-cleanup fixture, plus nine rejected private-copy mutations. Password Enter/button submit, empty/busy rejection, cancel/reopen/reset and owner-shadow routing assert exact SSID/password signals and inert harness-owner connect requests; not real WiFiPanel lifecycle or backend authorization.

## Known gaps (current cycle)

- Extracted-function cases in `Tests/network-service-guards.test.js` cover connectivity transitions, stale ping rejection, overlap prevention, and failure handling; live connectivity/ping integration remains unverified.
- The five adapter-boundary diagnostics recorded at `484030b62` are closed. One unsuppressed Process.environment QVariantMap→QVariantHash `incompatible-type` warning remains. The older simple-service lint gate still expects five removed warnings; its stale expectation is not evidence of a NetworkService regression: [testing](testing.md#simple-service-cohort).
- Private runtime cases do not establish live NetworkManager, connectivity/ping, disconnect, failed-start, or whole-shell integration.
- Production-list coverage uses inert services and fixture styling/translations; it preserves caller-provided order rather than exercising panel sorting, and verifies forget signals rather than NetworkManager deletion. Separate WiFiPanel coverage now exercises panel sorting and action routing with inert networking; neither harness establishes live networking/backend authorization, all locales/scales, or pointer/keyboard event delivery (actions invoke signals directly).

## Out of scope

- Bluetooth and airplane-mode state belongs in a separate Bluetooth spec.
- System monitor network throughput belongs in a separate system monitor spec.
