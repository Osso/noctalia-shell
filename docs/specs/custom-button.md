Custom button covers the configurable button widget used in the bar and Control Center. Runtime source lives in [Modules/Bar/Widgets/CustomButton.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Bar/Widgets/CustomButton.qml), [Modules/Panels/ControlCenter/Widgets/CustomButton.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Panels/ControlCenter/Widgets/CustomButton.qml), and their settings UIs.

## What it must do

Bar custom button:
- [x] Text command execution must fail closed when the configured text command is empty.
- [x] Text command execution must not replace or restart an already running text process.
- [x] Text command execution must run non-empty commands through `sh -lc`.

Control Center custom button:
- [x] Settings updates must copy left, right, and middle click commands from widget settings.
- [x] Settings updates must parse state-check JSON, copy tooltip text, copy state-logic enablement, and refresh state.
- [x] Missing settings must leave the current command/state values unchanged and must not refresh state.
- [x] Malformed state-check JSON and valid JSON that is not an array must clear parsed checks and log the parse failure. Missing command and tooltip settings use defaults; configured state-logic enablement is preserved, but empty checks restore the default icon and inactive state without launching a check.
- [x] State checking must skip null or commandless checks until it finds a command to execute.
- [x] State checking must assign the selected command as `['sh', '-c', command]` before starting the process, capturing that check's icon (or widget icon, then `heart`) for its result. Checks must not overlap a running state process.
- [x] A current check's zero exit must activate its captured icon; a nonzero exit must advance to the next check.
- [x] Every state refresh must invalidate previous results, stop the pending timer, and reset traversal. Enabled nonempty checks restart a 200 ms one-shot debounce using the latest settings.
- [x] A stale process exit must neither activate its old icon nor advance the new traversal. Replacement checks must wait for the old process to exit and the new debounce to expire, in either order; disabling state logic while a check runs must remain inactive after its exit.
- [x] State checking must fall back to the default icon and inactive state when no checks match.
- [x] State updates must clear hot state and restore the default icon when state logic is disabled or no parsed checks exist.
- [x] State updates must restart the state timer only when state logic is enabled and parsed checks exist.
- [x] Tooltip text must include configured left, right, and middle click command lines after the general tooltip text.

Settings and typed contracts:
- [x] Bar custom button settings preserve explicit falsey values such as `false`, `0`, and empty strings instead of replacing them with defaults.
- [x] Bar custom button settings prefer saved widget data over metadata defaults, while falling back to metadata for missing values.
- [x] Bar custom button settings save icon, click commands, wheel commands, text command, JSON parsing, stream mode, text lengths, and text interval into one settings object.
- [x] Bar custom button settings save unified wheel mode when separate wheel handling is disabled.
- [x] Control Center widget settings dialogs must load the custom button settings component and pass widget data plus metadata.
- [x] Custom button state-check settings delegates must type the `command`, `icon`, and `index` roles and use typed role properties instead of dynamic model fields.

## How it works

- [ ] See [docs/wiki/systems/custom-button.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/wiki/systems/custom-button.md).

## Implementation inventory

- [Modules/Bar/Widgets/CustomButton.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Bar/Widgets/CustomButton.qml) - bar widget command execution, text-command process, display content, and per-instance settings.
- [Modules/Panels/ControlCenter/Widgets/CustomButton.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Panels/ControlCenter/Widgets/CustomButton.qml) - Control Center shortcut command handling, state checks, hot icon state, and tooltip construction.
- [Modules/Panels/Settings/Bar/WidgetSettings/CustomButtonSettings.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Panels/Settings/Bar/WidgetSettings/CustomButtonSettings.qml) - bar custom button settings.
- [Modules/Panels/Settings/ControlCenter/WidgetSettings/CustomButtonSettings.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Panels/Settings/ControlCenter/WidgetSettings/CustomButtonSettings.qml) - Control Center custom button settings and typed state-check delegate.
- [Modules/Panels/Settings/ControlCenter/ControlCenterWidgetSettingsDialog.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Panels/Settings/ControlCenter/ControlCenterWidgetSettingsDialog.qml) - Control Center widget settings dialog loader.
- [Services/UI/BarWidgetRegistry.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Services/UI/BarWidgetRegistry.qml) - bar custom button metadata and settings mapping.
- [Services/UI/ControlCenterWidgetRegistry.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Services/UI/ControlCenterWidgetRegistry.qml) - Control Center custom button metadata and configurable-widget registration.

## Tests asserting this spec

- `Tests/custom-button-warnings.test.py behavior` runs the production Control Center button offscreen with synthetic Process/Quickshell and button fixtures: settings/click commands/tooltip/missing settings, ordered skips and failure-to-success traversal, all-fail and missing-icon results, disable-during-run, replacement before/after debounce, latest-settings debounce, and malformed/null/object JSON rejection. Ten behavior rows plus init/cleanup produce 12 reported passes. No real commands or desktop input are exercised.
- `Tests/custom-button-warnings.test.py lint` requires zero qmllint warnings and exit status zero. The final block-scoped `var` warning was removed at `f58175c90` (1→0); reported verification recorded six JS tests and 12 QML passes. Synthetic Process coverage does not establish real command execution or live-shell behavior.

- [Tests/bar-action-helper-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/bar-action-helper-guards.test.js)
- [Tests/custom-button-settings-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/custom-button-settings-guards.test.js)
- [Tests/custom-button-widget-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/custom-button-widget-guards.test.js)
- [Tests/panel-lock-palette-helper-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/panel-lock-palette-helper-guards.test.js)
- [Tests/qml-type-annotations.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/qml-type-annotations.test.js)

## Known gaps (current cycle)

- [ ] Add executable coverage for bar custom button click, wheel, JSON text parsing, and scrolling behavior.
- [ ] Add real Process integration coverage for Control Center custom button exits; current ordering/exit coverage uses synthetic processes.

## Out of scope

- Shared bar registry behavior is covered by [docs/specs/bar.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/bar.md).
- Shared Control Center shortcut registry behavior is covered by [docs/specs/control-center.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/control-center.md).
