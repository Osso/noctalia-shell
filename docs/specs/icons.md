Icons covers bundled icon-font loading, theme/desktop icon path resolution, and the shared icon picker. Runtime source lives mainly in `Commons/Icons.qml` and `Commons/ThemeIcons.qml`; implementation notes belong in [docs/wiki/systems/icons.md](../wiki/systems/icons.md).

## What it must do

### Icon font lifecycle

- [x] Icon codepoint lookup resolves aliases before reading the icon map.
- [x] Icon codepoint lookup returns mapped codepoints and leaves missing icons unresolved.
- [x] Icon codepoint lookup uses a typed string icon-name input.
- [x] Icon font loading destroys any previous dynamic font loader before creating a replacement.
- [x] Icon font loading creates a cache-busted `FontLoader` under the icon singleton root.
- [x] Dynamic font-loader object names include the current font version.
- [x] Icon font loading connects to the new loader's status changes.
- [x] Ready font-load status emits the font-reloaded signal and logs the loaded font name and version.
- [x] Error font-load status logs the failed version and does not emit the font-reloaded signal.
- [x] Manual font reload increments the font version before loading the next cache-busted font.

### Theme icon lookup

- [x] Named icon lookup delegates to the theme icon resolver with the current Quickshell icon theme and fallback name.
- [x] Named icon lookup fails closed to an empty path when resolver lookup throws.
- [x] Named icon lookup uses a typed string icon-name input while keeping fallback icon optional.
- [x] Desktop-entry icon lookup prefers `DesktopEntries.heuristicLookup` when available.
- [x] Desktop-entry icon lookup uses a typed string app-id input while keeping fallback icon optional.
- [x] Desktop-entry icon lookup falls back to `DesktopEntries.byId` when heuristic lookup is unavailable.
- [x] Desktop-entry icon lookup uses `application-x-executable` as the default fallback icon.
- [x] Empty, unknown, or failed desktop-entry lookups resolve through the fallback icon name.
- [x] Distro logo lookup returns the OS-provided distro icon path when present.
- [x] Distro logo lookup fails closed to an empty path when OS info is missing or empty.

### Icon picker

- [x] Opening restores selection and search from the initial icon; reopening replaces the previous state.
- [x] Search receives keyboard focus, trims/lowercases input, filters icon names, and Escape closes without emitting a selection.
- [x] A single click updates selection and its border without emitting; Apply is disabled for empty selection and otherwise emits the selected name once and closes.
- [x] Filtering to no matches and back recreates usable delegates; double-click emits the recreated delegate's icon once and closes.
- [x] Cancel closes without emission; opening a second picker preserves independent selection when the first is reopened and clicked.

## How it works

- [docs/wiki/systems/icons.md](../wiki/systems/icons.md)

## Implementation inventory

- `Commons/Icons.qml` - Tabler icon map access, dynamic icon-font loading, cache busting, and reload signaling.
- `Commons/IconsTabler.qml` - generated Tabler icon names, aliases, and codepoints.
- `Commons/ThemeIcons.qml` - theme-icon, desktop-entry, and distro-logo path helpers.
- `Helpers/ThemeIconResolver.js` - icon theme path resolver used by `ThemeIcons`.
- `Widgets/NIcon.qml` - shared icon-font rendering wrapper.
- `Widgets/NIconPicker.qml` - searchable icon selection popup.

## Tests asserting this spec

- `Tests/residual-singleton-owners.test.py runtime` — at `159c2d307`, Icons callback owner warnings drop 1→0. Offscreen actual Icons checks mapped lookup and a directly emitted `Quickshell.reloadCompleted` signal incrementing font version once and reaching `FontLoader.Ready`, including callback-local owner shadows. A host TrueType font substitutes for the bundled Tabler font; this proves neither Tabler glyph rendering nor canonical hot reload. Gates: [testing](testing.md#residual-singleton-owners).
- `Tests/icons-guards.test.js`
- `Tests/theme-icons-guards.test.js`
- `Tests/source-coverage.test.js`
- `Tests/icon-picker-warnings.test.py` and `Tests/Qml/IconPickerWarningsHarness.qml` - standalone picker lint and production-control offscreen behavior.

### Icon picker isolated evidence

- At `01034c9a4`, picker warnings drop 17→0. Five behavioral tests plus QtTest init/cleanup yield seven reported passes, covering the picker requirements above with four fixture icon names.
- `pragma ComponentBehavior: Bound` and explicit `required property string modelData` have behavioral backing: filtered delegate recreation, click/double-click payloads, and two picker instances exercise delegate data and owner isolation. This is not merely warning-count proof.
- Production picker/grid/input/buttons run with inert singleton services and icon data. Synthetic offscreen keyboard/mouse events prove focus and selection routing, not native desktop input, pixel rendering, the full icon catalogue, persistence, or whole-shell acceptance. Runner modes and acceptance checks: [testing](testing.md#icon-picker-isolated-runtime).

## Known gaps (current cycle)

- [ ] Add executable coverage for `NIcon` fallback rendering and warning behavior.
- [ ] Add fixture coverage for icon-theme resolver path precedence across theme directories.

## Out of scope

- Feature-specific icon choices are covered by their owning feature specs.
- Host OS logo candidate building is covered by [host-service.md](host-service.md).
