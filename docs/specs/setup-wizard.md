Setup Wizard covers first-run onboarding launch, completion, and selected setup persistence. Runtime source lives mainly in `shell.qml` and `Modules/Panels/SetupWizard/SetupWizard.qml`; implementation notes belong in [docs/wiki/systems/setup-wizard.md](../wiki/systems/setup-wizard.md).

## What it must do

### Launch gating

- [x] Setup wizard launch is skipped when setup is disabled.
- [x] Setup wizard launch is skipped on NixOS.
- [x] Setup wizard launch waits for host readiness before starting the setup timer.
- [x] Setup wizard launch starts the setup timer when setup is enabled and host state is ready.
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
- `Tests/setup-wizard-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for the close timer timeout and settings-saved close path.
- [ ] Add executable coverage for setup appearance and customization step value handoff.
- [ ] Add executable coverage for setup dock and wallpaper step integration beyond typed delegates.

## Out of scope

- Dock monitor semantics are covered by [dock.md](dock.md).
- File-picker behavior is covered by [file-picker.md](file-picker.md).
- Wallpaper service behavior is covered by [wallpaper.md](wallpaper.md).
