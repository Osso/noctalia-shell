Setup Wizard covers first-run onboarding launch, completion, and selected setup persistence. Runtime source lives mainly in `shell.qml` and `Modules/Panels/SetupWizard/SetupWizard.qml`; implementation notes belong in [docs/wiki/systems/setup-wizard.md](../wiki/systems/setup-wizard.md).

## What it must do

### Launch gating

- [x] Setup wizard launch is skipped when setup is disabled.
- [x] Setup wizard launch is skipped on NixOS.
- [x] Setup wizard launch waits for host readiness without deferred polling; HostService state changes re-run the gate.
- [x] Setup wizard launch remains skipped after terminal host metadata failure instead of guessing that the host is non-NixOS.
- [x] Setup wizard launch starts the setup timer only when setup is enabled and valid host state is ready.
- [x] The timer callback re-checks setup eligibility and NixOS state before opening, so recovery cannot open onboarding on NixOS.
- [x] Setup wizard display no-ops when no Quickshell screens are available.
- [x] Setup wizard display opens the `setupWizardPanel` on the first screen when the panel is loaded.
- [x] Setup wizard display restarts the setup timer when the target panel is not loaded yet.

### Completion and persistence

- [x] Setup completion ignores duplicate completion attempts and leaves settings, wallpaper changes, and close timer untouched.
- [x] Setup completion applies selected wallpaper directory and wallpaper, selected UI scale, and bar position before saving.
- [x] Setup completion starts the close timer after a successful save request.
- [x] Setup completion still persists UI choices when the wallpaper service is unavailable.
- [x] Setup completion resets completion state and avoids closing when saving throws.
- [x] Wallpaper settings update the stored wallpaper directory and refresh the wallpaper list only when the directory changes.
- [x] Wallpaper settings apply selected wallpapers only when a non-empty wallpaper is selected.
- [x] UI settings persist selected scale ratio and bar position.

### Wallpaper step

- [x] Setup wallpaper filtering mirrors the current wallpaper list.
- [x] Setup wallpaper refresh clears wallpaper lists when no directory is selected.
- [x] Setup wallpaper refresh reads the current screen list from the wallpaper service and selects the first wallpaper when none is selected.
- [x] Setup wallpaper refresh falls back to a directory scanner when the wallpaper service list helper is unavailable.
- [x] Setup wallpaper directory scanning starts a command for `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`, and `.svg` files.
- [x] Setup wallpaper directory scanning uses a typed string directory-path input.

### Setup layout geometry

- [x] Appearance, customization, dock, and wizard content preserve actual child geometry and text at widths 480/1000 and UI scales 1/1.25 when layout-owned dimensions become preferred sizes.
- [x] Appearance geometry covers both wallpaper-color modes, including scheme swatches.
- [x] Wizard progress geometry preserves the hidden final connector's 40 × 2 size as well as visible child geometry.
- [x] Geometry regression runs only offscreen with isolated writable paths, inert external services, and fixture-owned settings without real-config access.

### Typed delegates

- [x] Setup progress delegates expose typed step icon and label aliases instead of repeatedly reading implicit `modelData`.

## How it works

- [docs/wiki/systems/setup-wizard.md](../wiki/systems/setup-wizard.md)

## Implementation inventory

- `shell.qml` - first-run setup gating, setup timer, panel lookup, and retry behavior.
- `Modules/Panels/SetupWizard/SetupWizard.qml` - setup panel, selected values, completion flow, wallpaper settings, UI settings, and progress delegate.
- `Modules/Panels/SetupWizard/SetupAppearanceStep.qml` - setup-time appearance selection.
- `Modules/Panels/SetupWizard/SetupCustomizeStep.qml` - setup-time customization selection.
- `Modules/Panels/SetupWizard/SetupDockStep.qml` - setup-time dock monitor selection.
- `Modules/Panels/SetupWizard/SetupWallpaperStep.qml` - setup-time wallpaper selection.

## Tests asserting this spec

- `Tests/shell-setup-wizard-guards.test.js`
- `Tests/setup-wallpaper-step-guards.test.js`
- `Tests/setup-wizard-guards.test.js`
- `Tests/setup-layout-geometry.test.py` — 20 offscreen production-component geometry/content cases compared with tracked fixtures: eight appearance cases and four each for customization, dock, and initial wizard content. Recursive snapshots include hidden children. Run standalone with `python3 Tests/setup-layout-geometry.test.py --artifacts <new-directory>`.
- The same script's `--wizard-transitions` mode captures 52 snapshots: 13 forward/back step states across widths 480/1000 and scales 1/1.25. Assertions cover all five steps, wallpaper directory/image and customization scale/bar handoff, a changed-scale probe at 1.1, finish/skip save requests and settings-saved close state, duplicate completion, disabled Escape, and cancellation without saving. Transition geometry comparison requires `--expected <pre-change-capture>`; no tracked transition golden is implied. Buttons and selection signals are invoked directly, settings/services are fixtures, and animations are disabled: this is not physical input, real persistence, or visible-panel acceptance.
- Targeted `SetupWizard.qml` unqualified-access warnings fell from 48 to zero after owner qualification; this is not a zero-total-warning claim or an intended behavior change.
- `Tests/Qml/SetupLayoutGeometryHarness.qml` — production step and wizard-content instantiation without opening SmartPanel. Reported harness warnings fell 41→0 after owner qualification at `d6da20595`. Standalone `python3 Tests/setup-layout-geometry.test.py lint-harness` stages the runtime fixture sources with temporary singleton-aware module declarations; the static checker dispatches it exactly once. At `8fe0cc5d6`, acceptance requires qmllint success and no emitted `Warning:` lines; an injected warning exits 1 even when qmllint exits zero. This is harness-only static proof, not global warning-free acceptance; geometry/navigation coverage and limits above remain unchanged.
- At `0e62615da`/`a07dd776a`/`d8bdb9a49`, geometry capture uses default-settings bytes in a private synthetic HOME, creates a `0600` fixture and byte-for-byte `0600` backup, verifies the backup hash before staging, and checks fixture bytes after execution. `Tests/setup-layout-isolation.test.py` covers denied real-settings access with absent synthetic HOME, retained 20 geometries/52 transitions, no-argument temporary cleanup, pure lint without settings access, fixture-mutation rejection, and injected runtime-warning rejection. Successful captures check fixture/backup bytes and permissions; short temporary paths avoid IPC socket length failures. Safety details: [testing](testing.md#tests-asserting-this-spec).
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

### Customization isolated evidence

- At `07c412dea`/`56791a2ec`, `SetupCustomizeStep.qml` warnings drop 12→0. Standalone `Tests/setup-customize-warnings.test.py lint|behavior --artifacts <new-directory>` covers production customization with synthetic settings; no runner integration is claimed.
- Four offscreen cases (widths 480/1000 × scales 1/1.25) assert scale draft values/text/signals, opacity values/text, floating/shadow toggles, bar-position signals, density selection, active labels/colors, external selection updates, and reversed models. `Bound` ownership is exercised through delegate recreation and two simultaneous instances with independent scale/position state and no cross-instance signals.
- Direct signal invocation is component proof, not physical input or live-wizard acceptance. Behavior verifies no save requests and unchanged real-settings bytes after a permission-locked, hash-verified backup; real persistence remains untested. Isolation and acceptance gates: [testing](testing.md#setup-customization-isolated-runtime).

### Setup wallpaper isolated evidence

- At `9d8cac1b3`, `SetupWallpaperStep.qml` warnings drop 7→0 after qualifying scanner state owners and reading the named `StdioCollector`. `Tests/setup-wallpaper-warnings.test.py` reports seven isolated cases: four selection/preview geometry cases at widths 480/1000 × scales 1/1.25, directory signals, next/back selection retention, and scanner completion.
- Geometry cases use synthetic thumbnail clicks and assert selection signals, preview path/visibility/border/size, thumbnail dimensions, and empty-directory clearing. Directory coverage invokes editing/picker signals with empty and selected paths; next/back invokes button signals and checks draft retention, fixture wallpaper application, and no save requests.
- Scanner coverage runs real Process/StdioCollector with synthetic Python stdout: trim/blank filtering, first selection, preserving an existing selection, and unchanged list on failure. The reported wrong-collector negative control fails; it is not a built-in runner mode. No actual directory scan, wallpaper decoding/application, native picker, real persistence, or live wizard acceptance is proven. Isolation and gates: [testing](testing.md#setup-wallpaper-isolated-runtime).

## Known gaps (current cycle)

- [ ] Add executable coverage for the close timer timeout; settings-saved close state is covered with a fixture signal, not real persistence or completed panel teardown.
- [ ] Add executable coverage for setup appearance step value handoff; customization scale/bar signal handoff is covered.
- [ ] Add executable coverage for setup dock step integration beyond typed delegates.
- [ ] Extend isolated setup wallpaper selection/directory-signal coverage to native directory-picker integration and live wizard acceptance.

## Out of scope

- Dock monitor semantics are covered by [dock.md](dock.md).
- File-picker behavior is covered by [file-picker.md](file-picker.md).
- Wallpaper service behavior is covered by [wallpaper.md](wallpaper.md).
