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

- `Tests/context-menu-isolation.test.py` — private context-menu runtime/behavior entrypoints, denied host settings, fixture integrity and cleanup.

- `Tests/context-menu-warnings.test.py` — standalone `lint` and `runtime`; production NContextMenu warnings reported 10→0 at `a1b8afe27`.
- `Tests/Qml/ContextMenuWarningsHarness.qml` — five behavioral tests plus QtTest init/cleanup: seven reported offscreen passes. Covers layout/items, pointer activation/close ordering, explicit focus/Space/Escape, position/reopen/model replacement, and independent owners with recreated delegates.
- Runtime stages production NContextMenu/NListView with fixture settings/services under software/offscreen Qt. The child runs in bwrap with real config and its resolved destination masked; only the fixture directory is writable. The parent runner nevertheless reads real settings, creates a mode-0600 byte-for-byte hash-verified backup, and checks real bytes unchanged afterward. This docs audit does not execute that runner or read/hash real settings. Isolation and acceptance details: [testing](testing.md#context-menu-isolated-runtime).

## Known gaps (current cycle)

- [ ] Live compositor rendering/input, native focus delivery, hover behavior, real persistence and whole-shell acceptance remain unproven. Explicit `forceActiveFocus` and synthetic input are isolated component proof only.

## NPopupContextMenu isolated evidence

`Widgets/NPopupContextMenu.qml` is a separate Quickshell popup, not NContextMenu or PopupMenuWindow. Reported passes through `3a3706a43`/`258fc13c0`/`95f0e0838` back these requirements:

- [x] Open/reopen against independent anchors with default or explicit offsets; close through `close()` and `closeMenu()`.
- [x] Hide invisible rows, reject disabled activation, track hover and emit actions without automatically closing (the parent controls dismissal).
- [x] Close on Escape after explicit window activation and item focus.
- [x] Preserve independent heights, widths and action owners after model clearing/replacement and popup destruction/recreation under `ComponentBehavior: Bound`; closed owners disable row input without disabling another open owner.

`Tests/Qml/ButtonPopupWarningsHarness.qml` covers these four popup cases alongside two [button cases](buttons.md). `Tests/button-popup-warnings.test.py` reports NPopupContextMenu lint 4→1, retaining the unsuppressed `PopupAnchor.updateAnchor` missing-property metadata warning. Private-copy `--bound` exercises recreation; `popup-close` is a reported failing negative control. Runtime retains ten offscreen window-mask notices, not a clean runtime. Isolation and acceptance: [testing](testing.md#buttonpopup-isolated-runtime).

- [ ] Live compositor placement/input/focus, actual window-mask support, real persistence and whole-shell acceptance remain unproven; offscreen coordinates and synthetic events are component evidence only.

## Out of scope

- Layer-shell PopupMenuWindow surfaces belong to [popup context menu](popup-context-menu.md).
