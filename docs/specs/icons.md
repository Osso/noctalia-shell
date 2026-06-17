Icons covers bundled icon-font loading plus theme/desktop icon path resolution. Runtime source lives mainly in `Commons/Icons.qml` and `Commons/ThemeIcons.qml`; implementation notes belong in [docs/wiki/systems/icons.md](../wiki/systems/icons.md).

## What it must do

### Icon font lifecycle

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
- [x] Desktop-entry icon lookup prefers `DesktopEntries.heuristicLookup` when available.
- [x] Desktop-entry icon lookup falls back to `DesktopEntries.byId` when heuristic lookup is unavailable.
- [x] Desktop-entry icon lookup uses `application-x-executable` as the default fallback icon.
- [x] Empty, unknown, or failed desktop-entry lookups resolve through the fallback icon name.
- [x] Distro logo lookup returns the OS-provided distro icon path when present.
- [x] Distro logo lookup fails closed to an empty path when OS info is missing or empty.

## How it works

- [docs/wiki/systems/icons.md](../wiki/systems/icons.md)

## Implementation inventory

- `Commons/Icons.qml` - Tabler icon map access, dynamic icon-font loading, cache busting, and reload signaling.
- `Commons/IconsTabler.qml` - generated Tabler icon names, aliases, and codepoints.
- `Commons/ThemeIcons.qml` - theme-icon, desktop-entry, and distro-logo path helpers.
- `Helpers/ThemeIconResolver.js` - icon theme path resolver used by `ThemeIcons`.
- `Widgets/NIcon.qml` - shared icon-font rendering wrapper.

## Tests asserting this spec

- `Tests/icons-guards.test.js`
- `Tests/theme-icons-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for `Icons.get()` alias resolution and missing icon behavior.
- [ ] Add executable coverage for `NIcon` fallback rendering and warning behavior.
- [ ] Add fixture coverage for icon-theme resolver path precedence across theme directories.

## Out of scope

- Feature-specific icon choices are covered by their owning feature specs.
- Host OS logo candidate building is covered by [host-service.md](host-service.md).
