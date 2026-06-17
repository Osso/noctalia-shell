Popup Context Menu covers the shared popup menu widgets used by bar widgets and panel actions. Runtime source lives in `Widgets/NPopupContextMenu.qml` and `Widgets/NContextMenu.qml`; implementation notes belong in [docs/wiki/systems/popup-context-menu.md](../wiki/systems/popup-context-menu.md).

## What it must do

### Width and model handling

- [x] Menu width calculation ignores hidden items.
- [x] Menu width calculation measures label text from either `label` or `text`.
- [x] Menu width calculation includes icon width and spacing only for entries with an icon.
- [x] Menu width calculation includes horizontal margins and never drops below the minimum width.
- [x] Empty or missing menu models fall back to the minimum width.

### Opening and closing

- [x] Opening the menu requires an anchor item.
- [x] Missing anchor items log a warning and leave previous anchor, coordinates, and visibility unchanged.
- [x] Opening at coordinates recalculates width, stores the anchor item, stores x/y offsets, and makes the popup visible.
- [x] Opening schedules an anchor refresh when the popup anchor object is available.
- [x] Opening at an item defaults missing mouse coordinates to zero.
- [x] Opening helpers type anchor items and coordinate inputs.
- [x] Legacy context-menu opening helpers type coordinate and anchor inputs.
- [x] `closeMenu()` delegates to `close()`.
- [x] Closing the menu hides the popup.

### Typed delegates

- [x] Menu delegates expose typed aliases for item visibility, text, icon, enabled state, and action.
- [x] Menu delegate height and visibility use the typed item-visible alias.
- [x] Disabled menu entries reduce opacity.
- [x] Icon, label, click enablement, and triggered action use typed delegate aliases.

## How it works

- [docs/wiki/systems/popup-context-menu.md](../wiki/systems/popup-context-menu.md)

## Implementation inventory

- `Widgets/NPopupContextMenu.qml` - popup menu model, width calculation, anchor positioning, close helpers, and typed delegate roles.
- `Widgets/NContextMenu.qml` - legacy Popup-based context menu with typed delegate roles and open helpers.
- `Modules/Bar/Widgets/*.qml` - bar widget context-menu consumers.
- `Modules/Panels/Wallpaper/WallpaperPanel.qml` - panel action menu consumer.

## Tests asserting this spec

- `Tests/popup-context-menu-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for item click signal emission and parent-controlled closing.
- [ ] Add executable coverage for keyboard escape closing.
- [ ] Add executable coverage for click-outside behavior in the containing popup window.

## Out of scope

- Tray-specific menu behavior is covered by [tray.md](tray.md).
- Feature-specific menu models belong in their owning feature specs.
