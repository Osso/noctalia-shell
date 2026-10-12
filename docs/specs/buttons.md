# Buttons

`Widgets/NButton.qml` provides a labeled pointer-action button. Evidence below covers NButton only, not every button widget.

## What it must do

Reported isolated passes through `3a3706a43`/`258fc13c0`/`95f0e0838` back these requirements:

- [x] Dispatch left/right/middle actions on press without redispatch on release; reject disabled clicks and resume after re-enabling.
- [x] Track hover and emit enter/exit signals; accept explicit focus.
- [x] Use the button owner's tooltip despite a child property collision; hide it on press, exit and cancellation, clearing hover on cancellation.

## How it works

- [Isolated button/popup evidence](testing.md#buttonpopup-isolated-runtime).

## Implementation inventory

- `Widgets/NButton.qml` — label, pointer actions and tooltip ownership.

## Tests asserting this spec

- `Tests/Qml/ButtonPopupWarningsHarness.qml` — two button cases within six combined button/popup cases; synthetic pointer input and direct cancellation signal.
- `Tests/button-popup-warnings.test.py` — reported NButton lint reduction 4→0; owner-shadow coverage and failing `button-owner` negative control. Shared isolation, acceptance and residual runtime notices: [testing](testing.md#buttonpopup-isolated-runtime).

## Known gaps (current cycle)

- [ ] Native compositor input/focus, real tooltip service integration and whole-shell acceptance remain unproven. Isolated runtime is not diagnostic-free.

## Out of scope

Other button widgets and [popup context menus](context-menu.md#npopupcontextmenu-isolated-evidence).
