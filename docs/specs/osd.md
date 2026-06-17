OSD covers the on-screen display module and its settings tab for location, size, duration, enabled OSD types, and monitor filtering. Runtime source lives mainly in [Modules/OSD/OSD.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/OSD/OSD.qml) and [Modules/Panels/Settings/Tabs/OsdTab.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Panels/Settings/Tabs/OsdTab.qml).

## What it must do

Settings type helpers:
- [x] Adding an OSD type must append a missing type without mutating the input list.
- [x] Adding an OSD type must keep an existing type only once.
- [x] Adding an OSD type to a missing list must return a list containing that type.
- [x] Removing an OSD type must filter all matches without mutating the input list.
- [x] Removing an OSD type from a missing list must return an empty list.
- [x] Removing an OSD type that is absent must preserve the existing list.

Typed settings delegates:
- [x] OSD type option delegates must type the scalar `type` and `key` roles and use those typed roles for labels and enabled-type membership.
- [x] OSD type option delegates must not use dynamic `modelData.type` or `modelData.key` reads.
- [x] OSD monitor delegates must expose null-safe typed aliases for screen name, model, width, and height.
- [x] OSD monitor labels, scale lookup, descriptions, selection checks, and add/remove actions must use the typed monitor aliases.

## How it works

- [ ] See [docs/wiki/systems/osd.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/wiki/systems/osd.md).

## Implementation inventory

- [Modules/OSD/OSD.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/OSD/OSD.qml) - runtime OSD surfaces and OSD type handling.
- [Modules/Panels/Settings/Tabs/OsdTab.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Panels/Settings/Tabs/OsdTab.qml) - OSD settings helpers, type toggles, and monitor toggles.
- [Assets/settings-default.json](/syncthing/Sync/Projects/apps/noctalia-shell/Assets/settings-default.json) - default OSD settings.

## Tests asserting this spec

- [Tests/osd-tab-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/osd-tab-guards.test.js)
- [Tests/qml-type-annotations.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/qml-type-annotations.test.js)

## Known gaps (current cycle)

- [ ] Add executable coverage for OSD runtime display, auto-hide, positioning, and type filtering.
- [ ] Add executable coverage for monitor add/remove helper behavior.

## Out of scope

- Audio OSD suppression behavior is covered by [docs/specs/audio.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/audio.md).
- Brightness OSD display behavior is covered by [docs/specs/brightness.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/brightness.md).
