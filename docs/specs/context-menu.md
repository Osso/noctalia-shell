# Context menu

`Widgets/NContextMenu.qml` provides a model-backed Qt Quick popup. Isolated evidence below covers this component, not [PopupMenuWindow](popup-context-menu.md).

## What it must do

Reported offscreen passes at `a1b8afe27` back these requirements:

- [x] Render label/text, icon and action/key/index values; hide invisible rows, disable activation of disabled rows, and update row height/padding bindings.
- [x] Emit the selected action while visible, then close; reopen and accept replacement or empty models.
- [x] Accept Space activation after explicit delegate focus and Escape dismissal without another action.
- [x] Map item-relative positions with and without offsets.
- [x] Preserve independent menu owners and their dimensions after delegate recreation under `ComponentBehavior: Bound`.

## How it works

- [Popup context-menu surfaces](popup-context-menu.md).

## Implementation inventory

- `Widgets/NContextMenu.qml` — popup, model delegates, action signal and positioning helpers.
- `Widgets/NListView.qml` — menu list and scrolling.

## Tests asserting this spec

- `Tests/context-menu-warnings.test.py` — standalone `lint` and `runtime`; production NContextMenu warnings reported 10→0 at `a1b8afe27`.
- `Tests/Qml/ContextMenuWarningsHarness.qml` — five behavioral tests plus QtTest init/cleanup: seven reported offscreen passes. Covers layout/items, pointer activation/close ordering, explicit focus/Space/Escape, position/reopen/model replacement, and independent owners with recreated delegates.
- Runtime stages production NContextMenu/NListView with fixture settings/services under software/offscreen Qt. The child runs in bwrap with real config and its resolved destination masked; only the fixture directory is writable. The parent runner nevertheless reads real settings, creates a mode-0600 byte-for-byte hash-verified backup, and checks real bytes unchanged afterward. This docs audit does not execute that runner or read/hash real settings. Isolation and acceptance details: [testing](testing.md#context-menu-isolated-runtime).

## Known gaps (current cycle)

- [ ] Live compositor rendering/input, native focus delivery, hover behavior, real persistence and whole-shell acceptance remain unproven. Explicit `forceActiveFocus` and synthetic input are isolated component proof only.

## Out of scope

- Layer-shell popup surfaces belong to [popup context menu](popup-context-menu.md).
