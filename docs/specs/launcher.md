Launcher covers launcher panel search state, plugin registration, command routing, result aggregation, launcher IPC modes, and built-in application, calculator, clipboard, and emoji plugin contracts. Runtime source lives mainly in `Modules/Panels/Launcher/Launcher.qml`; implementation notes belong in [docs/wiki/systems/launcher.md](../wiki/systems/launcher.md).

## What it must do

### Launcher shell

- [x] Search text updates are stored on the launcher.
- [x] Plugin registration stores plugins, gives each plugin a launcher back-reference, and initializes plugins that expose an init hook.
- [x] Result updates clear previous results and active plugin state before recalculating.
- [x] Command-mode searches route to the first plugin that handles the command text and expose that plugin's results.
- [x] Bare command prefix searches aggregate commands from command-capable plugins.
- [x] Command searches strip the command prefix before fuzzy command filtering and unwrap fuzzy results.
- [x] Launcher IPC can open normal, clipboard, calculator, and emoji modes through the target screen.
- [x] Launcher result delegates type `modelData` and `index` roles for both list and grid views.
- [x] Launcher result delegates use typed display/image/emoji aliases instead of repeated dynamic field access.
- [x] Launcher active plugin and plugin back-references are typed.

### Applications plugin

- [x] Applications plugin exposes lifecycle/category hooks and category metadata.
- [x] Application categories are parsed from string/list desktop-entry fields, trimmed, deduplicated, and normalized.
- [x] Application category matching supports all, audio/video, education/science, system/utility/settings, and priority matching.
- [x] Application loading/search helpers include executable/search fields and protect missing data.
- [x] Application results support launch paths and usage tracking.
- [x] Application usage keys prefer app id, then command, then name, then `unknown`.
- [x] Usage counts ignore missing maps and non-finite stored values.
- [x] Usage recording increments existing counts, initializes new counts, and debounces persistence.

### Calculator plugin

- [x] Calculator evaluation supports arithmetic precedence, parentheses, division, modulo, and decimal rounding.
- [x] Calculator evaluation rejects unsafe characters, identifiers, empty input, invalid expressions, and non-finite results.
- [x] Calculator math-expression detection accepts only supported math characters and rejects commands/functions.

### Clipboard plugin

- [x] Clipboard plugin command and result helpers handle clipboard mode only.
- [x] Clipboard plugin image metadata parsing and image entry formatting keep image results structured.
- [x] Clipboard plugin text entry formatting keeps text results structured.
- [x] Clipboard result activation delegates to clipboard service operations and closes the launcher.

### Emoji plugin

- [x] Emoji plugin initialization logs startup, selects categories, and refreshes results when categories change.
- [x] Emoji command entry point exposes `>emoji`, description, icon, and activation behavior.
- [x] Emoji results fail closed when invoked outside emoji mode.
- [x] Emoji results show a loading row before emoji data is loaded.
- [x] Bare emoji command searches the selected category and enters browsing mode.
- [x] Emoji query command searches by text and leaves browsing mode.
- [x] Emoji result formatting includes name, keyword/category description, emoji character, and activation that copies the emoji and closes the launcher.

## How it works

- [docs/wiki/systems/launcher.md](../wiki/systems/launcher.md)

## Implementation inventory

- `Modules/Panels/Launcher/Launcher.qml` - launcher panel state, plugin registry, command/result routing, and list/grid result views.
- `Modules/Panels/Launcher/ClipboardPreview.qml` - clipboard preview UI.
- `Modules/Panels/Launcher/Plugins/ApplicationsPlugin.qml` - application discovery, categorization, search, activation, and usage tracking.
- `Modules/Panels/Launcher/Plugins/CalculatorPlugin.qml` - calculator command handling and expression evaluation.
- `Modules/Panels/Launcher/Plugins/ClipboardPlugin.qml` - clipboard command handling and result formatting.
- `Modules/Panels/Launcher/Plugins/EmojiPlugin.qml` - emoji command handling, category browsing, search, and copy activation.
- `Services/Control/IPCService.qml` - launcher IPC mode routing.
- `Services/Keyboard/ClipboardService.qml` - clipboard data provider used by the clipboard plugin.
- `Services/Keyboard/EmojiService.qml` - emoji data provider used by the emoji plugin.

## Tests asserting this spec

- `Tests/launcher-guards.test.js`
- `Tests/applications-plugin-guards.test.js`
- `Tests/calculator-plugin-guards.test.js`
- `Tests/clipboard-plugin-guards.test.js`
- `Tests/emoji-plugin-guards.test.js`
- `Tests/qml-runtime-guards.test.js`
- `Tests/qml-type-annotations.test.js`

## Known gaps (current cycle)

- [ ] Add executable tests for plugin result activation paths that currently only have structural coverage.
- [ ] Add executable tests for launcher preview rendering and clipboard preview loading.
- [ ] Add concrete fixtures for desktop-entry application discovery and terminal launch fallbacks.

## Out of scope

- Clipboard service persistence belongs in [clipboard.md](clipboard.md).
- Emoji service persistence belongs in [emoji.md](emoji.md).
