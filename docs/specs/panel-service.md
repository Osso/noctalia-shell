PanelService covers shared panel registration, popup-menu window lookup, panel lookup, and single-open-panel coordination. Runtime source lives in `Services/UI/PanelService.qml`; implementation notes belong in [docs/wiki/systems/panel-service.md](../wiki/systems/panel-service.md).

## What it must do

### Registration

- [x] Panel registration stores panels by `objectName`.
- [x] Panel registration logs registered panel names.
- [x] Popup-menu window registration ignores missing screen or window arguments.
- [x] Popup-menu window registration stores windows by screen name.
- [x] Popup-menu window registration emits the popup-window registration signal.

### Lookup

- [x] Popup-menu window lookup returns null without a screen.
- [x] Popup-menu window lookup returns the matching screen window or null for unknown screens.
- [x] Panel lookup falls back to the first matching panel name when no screen is supplied.
- [x] Screen-specific panel lookup builds keys from panel name and screen name.
- [x] Screen-specific panel lookup returns an already registered screen panel.
- [x] Missing panel lookup logs a warning and returns null.
- [x] Panel existence checks query registered panel keys.

### Open and close coordination

- [x] Opening a panel closes a different already-open panel.
- [x] Opening a panel records it as the current open panel before emitting the open signal.
- [x] Opening a panel with a fake active panel closes the previous panel before emitting the open signal.
- [x] Closing a panel clears the current open panel only when it is the active panel.
- [x] Closing a panel emits the close signal.
- [x] Closing fake panels preserves a different active panel and clears the active panel before emitting the close signal.

## How it works

- [docs/wiki/systems/panel-service.md](../wiki/systems/panel-service.md)

## Implementation inventory

- `Services/UI/PanelService.qml` - shared singleton for panel registration, popup menu window registration, panel lookup, and active-panel coordination.

## Tests asserting this spec

- `Tests/panel-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add multi-screen fixture coverage for popup-menu windows and screen-specific panel keys.
- [ ] Add coverage for `lockScreen` consumers that depend on PanelService.

## Out of scope

- Individual panel rendering and settings behavior belongs in the specs for those panels.
- Lock-screen action dispatch is covered by [docs/specs/session-menu.md](session-menu.md).
