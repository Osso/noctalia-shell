Emoji covers emoji data loading, search, category browsing, usage tracking, clipboard copy, and launcher plugin integration. Runtime source lives mainly in `Services/Keyboard/EmojiService.qml` and `Modules/Panels/Launcher/Plugins/EmojiPlugin.qml`; implementation notes belong in [docs/wiki/systems/emoji.md](../wiki/systems/emoji.md).

## What it must do

### Search and popular results

- [x] Search fails closed before emoji data loads.
- [x] Blank search returns popular/recent emoji results.
- [x] Search normalizes query terms and requires every term to match some emoji field.
- [x] Search matches emoji glyphs, names, keywords, and categories.
- [x] Popular results read per-emoji usage counts, exclude unused emoji, sort by usage descending, sort ties by name, and apply the requested limit.

### Categories and usage

- [x] Category summaries fail closed before emoji data loads.
- [x] Category summaries group emoji by category, treating missing categories as `other`.
- [x] Category browsing filters by exact category.
- [x] The `recent` category uses the popular emoji fallback.
- [x] Usage recording ignores empty emoji values.
- [x] Usage recording increments existing and new emoji counts and schedules persistence.

### Data loading and persistence

- [x] Usage-file bootstrap creates a default usage JSON file.
- [x] Emoji loading waits for both user and built-in files before finalizing.
- [x] Finalization deduplicates emoji by glyph, loads built-ins first, and lets user emoji override duplicates.
- [x] Usage data reload reads the usage file.
- [x] Usage data save restarts the debounce timer.
- [x] Usage data write serializes counts, creates the destination directory, writes JSON, and logs save errors.

### Clipboard copy

- [x] Copy ignores empty emoji values.
- [x] Copy records usage before sending a nonempty emoji to `wl-copy`.
- [x] Copy writes the selected emoji through `wl-copy`.

### Launcher plugin

- [x] Plugin init logs initialization.
- [x] Category selection stores the selected category and refreshes launcher results when a launcher is present.
- [x] The `>emoji` command is exposed with translated description and activates by setting launcher search text.
- [x] Result lookup returns no results for unrelated commands and shows a loading row before emoji data is ready.
- [x] Browsing mode lists the selected category for `>emoji `.
- [x] Search mode lists search results for `>emoji <query>`.
- [x] Formatted launcher entries include name, keywords/category description, emoji glyph, and activate by copying the emoji and closing the launcher.

## How it works

- [docs/wiki/systems/emoji.md](../wiki/systems/emoji.md)

## Implementation inventory

- `Services/Keyboard/EmojiService.qml` - emoji data, search/category helpers, usage persistence, and clipboard copy.
- `Modules/Panels/Launcher/Plugins/EmojiPlugin.qml` - launcher command, category browsing, result formatting, and activation.
- `Services/Control/IPCService.qml` - launcher mode routing for emoji search.

## Tests asserting this spec

- `Tests/emoji-service-guards.test.js`
- `Tests/emoji-plugin-guards.test.js`
- `Tests/qml-runtime-guards.test.js`

## Known gaps (current cycle)

- [ ] Add executable tests for user/built-in emoji file parse handlers.
- [ ] Add executable tests for usage-file parse failure fallback.
- [ ] Add spec coverage for launcher category UI controls.

## Out of scope

- General launcher navigation/search behavior belongs in the launcher spec.
- Clipboard history belongs in [clipboard.md](clipboard.md).
