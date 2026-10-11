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

Bounded runtime regression:
- [x] Production OSD must suppress startup events, react to fixture audio/brightness/lock signals and device/monitor changes, restart auto-hide after updates, and unload/reset state after timeout in horizontal and vertical layouts; explicit hide must also unload/reset state.
- [x] Private headless Cage tests must isolate HOME/XDG/Noctalia paths, preserve real settings, clean up experimental processes, and retain all platform warnings. Content/state assertions are not compositor pixel, input, or layer-shell placement proof.

## How it works

- [ ] See [docs/wiki/systems/osd.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/wiki/systems/osd.md).

## Implementation inventory

- [Modules/OSD/OSD.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/OSD/OSD.qml) - runtime OSD surfaces and OSD type handling.
- [Modules/Panels/Settings/Tabs/OsdTab.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Panels/Settings/Tabs/OsdTab.qml) - OSD settings helpers, type toggles, and monitor toggles.
- [Assets/settings-default.json](/syncthing/Sync/Projects/apps/noctalia-shell/Assets/settings-default.json) - default OSD settings.

## Tests asserting this spec

- `Tests/osd-warnings.test.py behavior` with `Tests/Qml/OSDWarningsHarness.qml`: actual production component, inert services, one private Cage output; standalone, not added to the broad runner.
- `Tests/osd-warnings.test.py lint`: staged production `Modules/OSD/OSD.qml` requires zero warnings and exit status zero; residual 37 unqualified plus five missing-property warnings drop 42→0 at `baf99c712`. This is target-file static coverage, not project-wide warning-free acceptance.
- [Tests/osd-tab-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/osd-tab-guards.test.js)
- [Tests/qml-type-annotations.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/qml-type-annotations.test.js)

## Known gaps (current cycle)

- [ ] Cage layer-shell/platform warnings remain visible. Real compositor placement/pixels/input, multi-output independent timers, enabled-type rejection and suppression consumption remain outside the private Cage regression.
- [ ] Add executable coverage for monitor add/remove helper behavior.

## Out of scope

- Audio OSD suppression behavior is covered by [docs/specs/audio.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/audio.md).
- Brightness OSD display behavior is covered by [docs/specs/brightness.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/brightness.md).
