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
- [x] Invalid state-check JSON must clear parsed checks, reset missing command and tooltip settings to defaults, disable state logic, refresh state, and log the parse failure.
- [x] State checking must skip null or commandless checks until it finds a command to execute.
- [x] State checking must start the process executor when a valid check command is found.
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

- [Tests/bar-action-helper-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/bar-action-helper-guards.test.js)
- [Tests/custom-button-settings-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/custom-button-settings-guards.test.js)
- [Tests/custom-button-widget-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/custom-button-widget-guards.test.js)
- [Tests/panel-lock-palette-helper-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/panel-lock-palette-helper-guards.test.js)
- [Tests/qml-type-annotations.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/qml-type-annotations.test.js)

## Known gaps (current cycle)

- [ ] Add executable coverage for bar custom button click, wheel, JSON text parsing, and scrolling behavior.
- [ ] Add executable coverage for Control Center custom button process exit handling.

## Out of scope

- Shared bar registry behavior is covered by [docs/specs/bar.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/bar.md).
- Shared Control Center shortcut registry behavior is covered by [docs/specs/control-center.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/control-center.md).
