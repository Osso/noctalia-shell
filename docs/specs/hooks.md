Hooks covers user-configured shell commands that run after wallpaper and dark-mode changes. Runtime source lives mainly in `Services/Control/HooksService.qml`; implementation notes belong in [docs/wiki/systems/hooks.md](../wiki/systems/hooks.md).

## What it must do

### Wallpaper hooks

- [x] Wallpaper hooks do not run when hook settings are missing.
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

- `Tests/hooks-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for dark-mode hook launch failure logging.
- [ ] Add executable coverage for settings-tab manual test actions.
- [ ] Add executable coverage for hook defaults and settings schema shape.

## Out of scope

- Wallpaper selection and cache behavior are covered by [wallpaper.md](wallpaper.md).
- Color-scheme and dark-mode state behavior are covered by [dark-mode.md](dark-mode.md).
