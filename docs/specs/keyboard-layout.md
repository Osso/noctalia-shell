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

## How it works

- [docs/wiki/systems/keyboard-layout.md](../wiki/systems/keyboard-layout.md)

## Implementation inventory

- `Services/Keyboard/KeyboardLayoutService.qml` - layout-code normalization, current layout storage, and layout language map.
- `Modules/Bar/Widgets/KeyboardLayout.qml` - bar widget that displays the current layout and opens layout actions.
- `Modules/Panels/Settings/Bar/WidgetSettings/KeyboardLayoutSettings.qml` - settings UI for keyboard layout widget display mode.

## Tests asserting this spec

- `Tests/keyboard-layout-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for KeyboardLayout widget display modes.
- [ ] Add executable coverage for KeyboardLayout widget context-menu actions.
- [ ] Add executable coverage for keyboard layout settings persistence.
- [ ] Add executable coverage for compositor layout events reaching KeyboardLayoutService.

## Out of scope

- Compositor-specific keyboard layout parsing and event forwarding belong in [compositor.md](compositor.md).
- General bar widget placement belongs in [bar.md](bar.md).
