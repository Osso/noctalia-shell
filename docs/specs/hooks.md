Hooks covers user-configured shell commands that run after wallpaper and dark-mode changes. Runtime source lives mainly in `Services/Control/HooksService.qml`; implementation notes belong in [docs/wiki/systems/hooks.md](../wiki/systems/hooks.md).

## What it must do

### Wallpaper hooks

- [x] Wallpaper hooks do not run when hook settings are missing.
- [x] Wallpaper hook execution uses a typed wallpaper path input while keeping screen name optional.
- [x] Wallpaper hooks do not run when hooks are disabled.
- [x] Wallpaper hooks do not run when the configured wallpaper script is blank.
- [x] Wallpaper hook commands replace `$1` with the wallpaper path everywhere it appears.
- [x] Wallpaper hook commands replace `$2` with the screen name.
- [x] Wallpaper hook commands execute through `sh -c` using detached execution.
- [x] Wallpaper hook execution logs successful command execution.
- [x] Wallpaper hook commands use an empty screen-name fallback when the screen name is missing.
- [x] Wallpaper hook execution logs failures raised while launching the command.

### Dark-mode hooks

- [x] Dark-mode hooks do not run when hook settings are missing.
- [x] Dark-mode hook execution uses a typed boolean dark-mode state input.
- [x] Dark-mode hooks do not run when hooks are disabled.
- [x] Dark-mode hooks do not run when the configured dark-mode script is blank.
- [x] Dark-mode hook commands replace `$1` with `true` when dark mode is enabled.
- [x] Dark-mode hook commands replace `$1` with `false` when dark mode is disabled.
- [x] Dark-mode hook commands execute through `sh -c` using detached execution.

## How it works

- [docs/wiki/systems/hooks.md](../wiki/systems/hooks.md)

## Implementation inventory

- `Services/Control/HooksService.qml` - wallpaper and dark-mode hook execution.
- `Modules/Panels/Settings/Tabs/HooksTab.qml` - hook settings editor and manual test actions.
- `Assets/settings-default.json` - default hook settings shape.
- `Services/UI/WallpaperService.qml` - emits wallpaper change signals consumed by the hook service.

## Tests asserting this spec

- Through `68ad69e78`/`a8ffe4ef8`/`f3d9f4656`, HooksService warnings drop 2→0. `Tests/hooks-app-theme-warnings.test.py` and `Tests/Qml/HooksAppThemeWarningsHarness.qml` assert dark-mode hook ordering before deferred template delivery, wallpaper argument substitution, missing/disabled/blank hook guards, and simulated dark-mode launch failure logging without blocking template application. Seven normal and seven owner-shadow passes include QtTest init/cleanup, not seven behavioral tests. Commands are inert recorder fixtures; no real shell launch is proven. Shared isolation, four reported negative captures, and limits: [testing](testing.md#hooksapp-theme-services-isolated-runtime).

- At `18fed36d7`, HooksTab warnings drop 1→0. `Tests/Qml/NotificationsHooksWarningsHarness.qml` checks Loader-driven width changes, enabled-toggle visibility, wallpaper-command keyboard editing, unchanged theme command, and synthetic saved state on reopen. Hook execution fixtures throw if called; manual test actions are not invoked. No real hook execution, config access, or disk persistence is proven. Shared accounting and isolation: [testing](testing.md#notifications-hooks-settings-isolated-runtime).

- `Tests/hooks-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add real command-launch integration coverage for dark-mode hook failure logging; isolated coverage currently uses a throwing fixture.
- [ ] Add executable coverage for settings-tab manual test actions.
- [ ] Add executable coverage for hook defaults and settings schema shape.

## Out of scope

- Wallpaper selection and cache behavior are covered by [wallpaper.md](wallpaper.md).
- Color-scheme and dark-mode state behavior are covered by [dark-mode.md](dark-mode.md).
