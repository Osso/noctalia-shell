File Picker covers reusable file/folder picking, file icon mapping, size formatting, selection confirmation, filtering, and typed file delegates. Runtime source lives mainly in `Widgets/NFilePicker.qml`; implementation notes belong in [docs/wiki/systems/file-picker.md](../wiki/systems/file-picker.md).

## What it must do

### File icons and sizes

- [x] File icon mapping recognizes common text, image, video, music, archive, PDF/text, spreadsheet, and presentation extensions.
- [x] File icon mapping uses a typed file-name input.
- [x] Unknown extensions fall back to the generic file icon.
- [x] File size formatting renders bytes, KB, MB, and GB with the expected precision.
- [x] File size formatting uses a typed byte-size input.

### Opening and selection

- [x] Opening the picker initializes `currentPath` from `initialPath` when no current path exists.
- [x] Opening the picker preserves an existing current path.
- [x] Opening the picker requests selection reset and opens the popup.
- [x] Confirming with no current selection leaves selected paths unchanged, emits no accepted event, and does not close.
- [x] Confirming with a selection stores selected paths, emits the accepted event, and closes once.
- [x] Single-click file selection works only in file mode.
- [x] Single-click folder selection works only in folder mode.
- [x] Double-clicking a folder navigates into it.
- [x] Double-clicking a file in file mode selects and confirms it.

### Navigation

- [x] Parent-folder navigation updates both the folder model URL and current path.

### Search controls

- [x] Search-bar opening schedules focus for the search input.
- [x] Search-bar closing clears search/filter text and refreshes filtered results.
- [x] Toolbar, Ctrl+F, and Escape search controls route through the shared search visibility helper.

### Filtering

- [x] Filtering clears stale filtered rows before rebuilding results.
- [x] Filtering hides dotfiles when hidden files are disabled.
- [x] Filtering includes directories while searching file mode.
- [x] Filtering includes files whose names match the search text.
- [x] Folder-selection mode includes only directories.
- [x] Hidden files are included when hidden files are enabled.

### Types

- [x] Grid file delegates declare typed file name, path, directory flag, and size roles.
- [x] List file delegates declare typed file name, path, directory flag, and size roles.
- [x] File delegates use typed role properties instead of dynamic `model.file*` access.

## How it works

- [docs/wiki/systems/file-picker.md](../wiki/systems/file-picker.md)

## Implementation inventory

- `Widgets/NFilePicker.qml` - reusable picker popup, filesystem model, search/filtering, selection, icon/size helpers, grid/list delegates.
- `Modules/Panels/Settings/Tabs/GeneralTab.qml` - avatar file picker usage.
- `Modules/Panels/Settings/Tabs/WallpaperTab.qml` - wallpaper file/folder picker usage.
- `Modules/Panels/Settings/Tabs/ScreenRecorderTab.qml` - recording folder picker usage.
- `Modules/Panels/Settings/Bar/WidgetSettings/ControlCenterSettings.qml` - custom image picker usage.
- `Modules/Panels/SetupWizard/SetupWallpaperStep.qml` - setup-time wallpaper picker usage.

## Tests asserting this spec

- `Tests/file-picker-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for each settings/setup integration path.

## Out of scope

- Specific wallpaper behavior belongs in [wallpaper.md](wallpaper.md).
- Settings persistence belongs in [settings.md](settings.md).
