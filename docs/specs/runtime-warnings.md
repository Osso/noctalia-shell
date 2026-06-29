Runtime warning guards cover repeated QML/Qt warnings that obscure profiling and reload health. Runtime source spans the components that emit or trigger the warnings.

## What it must do

- [x] Cava process startup is gated by `ProgramCheckerService.cavaAvailable` so missing `cava` does not repeatedly spawn and warn.
- [x] Desktop-entry icon lookup rejects absolute/file URL icon values before passing them to the Qt icon resolver, avoiding repeated missing SVG warnings from stale launcher entries.
- [x] Process panel CPU warning colors use defined palette colors and do not reference undefined `Color.mWarning`.

## Implementation inventory

- `Services/Media/CavaService.qml` - Cava visualizer process lifecycle.
- `Commons/ThemeIcons.qml` - desktop-entry icon lookup and fallback sanitization.
- `Modules/Panels/Process/ProcessPanel.qml` - process CPU warning color bindings.

## Tests asserting this spec

- `Tests/runtime-warning-guards.test.js`
- `Tests/source-coverage.test.js`
