Keyboard Layout covers shell display of the current keyboard layout and normalization of compositor-provided layout names into short display codes. Runtime source lives mainly in `Services/Keyboard/KeyboardLayoutService.qml` and `Modules/Bar/Widgets/KeyboardLayout.qml`; implementation notes belong in [docs/wiki/systems/keyboard-layout.md](../wiki/systems/keyboard-layout.md).

## What it must do

### Layout code extraction

- [x] Missing or empty layout strings return the translated unknown-layout label.
- [x] Short layout codes are lowercased.
- [x] Variant suffixes such as `fr+oss` are removed before display.
- [x] Parenthesized layout codes such as `English (US)` and `German (DE)` are extracted.
- [x] Language-map matches take precedence over prefix fallback.
- [x] Unknown alphabetic layout names fall back to their first three lowercase characters.
- [x] Non-alphabetic layout names return the translated unknown-layout label.

### Current layout state

- [x] Setting the current layout stores the extracted display code.

### Bar widget

- [x] The Keyboard Layout widget renders the current layout as uppercase display text.
- [x] The Keyboard Layout widget tooltip includes the uppercase current layout.
- [x] Display mode `forceOpen` forces the pill open, `alwaysHide` forces it closed, and `onhover` leaves both force flags disabled.
- [x] The widget settings context-menu action closes the popup menu window before opening widget settings with the current widget identity.
- [x] Right clicking the widget opens its context menu at the BarService-provided pill position.

## How it works

- [docs/wiki/systems/keyboard-layout.md](../wiki/systems/keyboard-layout.md)

## Implementation inventory

- `Services/Keyboard/KeyboardLayoutService.qml` - layout-code normalization, current layout storage, and layout language map.
- `Modules/Bar/Widgets/KeyboardLayout.qml` - bar widget that displays the current layout and opens layout actions.
- `Modules/Panels/Settings/Bar/WidgetSettings/KeyboardLayoutSettings.qml` - settings UI for keyboard layout widget display mode.

## Tests asserting this spec

- At `2a73a4c4f`, KeyboardLayoutSettings warnings drop 2→0. The isolated editor case checks `onhover`/`forceOpen`/`alwaysHide`, metadata defaults, keyboard selection, copy-save retaining unrelated fields without source mutation, independent instances, and reopen from saved values. Shared accounting and limits: [testing](testing.md#small-widget-settings-isolated-runtime); no real layout changes or persistence proof.

- At `919e77989`/`5d0857b06`, `Tests/brightness-keyboard-services-warnings.test.py` reports KeyboardLayoutService diagnostics 4→0. One of three shared behavioral cases covers initial-layout toast suppression, timer initialization, subsequent normalized-layout toasts, duplicate/disabled/unknown-layout suppression, and previous-layout updates. `keyboard-timer` is a failing negative control; harness lint is zero-warning. Inert fixtures do not prove compositor event delivery or real configuration: [testing](testing.md#brightnesskeyboard-services-isolated-runtime).
- `Tests/keyboard-layout-service-guards.test.js`
- `Tests/keyboard-layout-widget-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [x] Add executable coverage for KeyboardLayout widget display modes.
- [x] Add executable coverage for KeyboardLayout widget context-menu actions.
- [ ] Add executable coverage for keyboard layout settings persistence.
- [ ] Add executable coverage for compositor layout events reaching KeyboardLayoutService.

## Out of scope

- Compositor-specific keyboard layout parsing and event forwarding belong in [compositor.md](compositor.md).
- General bar widget placement belongs in [bar.md](bar.md).
