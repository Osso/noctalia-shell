Helper utilities cover the reusable JavaScript helpers under [Helpers/](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers) for color conversion, calculator math, hashing, icon resolution, fuzzy search, Qt object conversion, text formatting, custom button content parsing, timer parsing, brightness parsing, and debug formatting.

## What it must do

Color helpers:
- [x] Color conversion must support hex/RGB/HSL/HSV conversion, clamp RGB values before hex output, compute luminance/contrast, classify light colors, adjust lightness/saturation, generate surface variants, and expose a stable color-list shape without duplicate name/color pairs.

Math and hashing:
- [x] Advanced math must convert degrees/radians, evaluate supported calculator functions/constants, format repeating/small numeric results, document supported function groups, and reject unsafe evaluation input.
- [x] SHA-256 must produce canonical hashes for empty input, `abc`, and the quick-brown-fox fixture.

Search and icons:
- [x] Theme icon resolution must prefer an existing primary icon, fall back to the configured fallback icon, return empty when neither exists, and never pass the fallback string as the `iconPath` boolean check argument.
- [x] Fuzzy search must return target/index/highlight data for a single match, filter ordered result lists, support object-key search, and expose matched objects.

Formatting and conversion:
- [x] Qt object conversion must drop Qt signal/object-name/function noise, recursively convert nested objects, convert numeric length-shaped objects into arrays, and stringify valid Qt colors.
- [x] Text display formatting must include font and `white-space: pre-wrap` styling while escaping HTML-sensitive characters.
- [x] Debug stringification must preserve readable JSON output for circular object graphs using circular-reference markers.

Custom button, timer, and brightness parsing:
- [x] Custom button content parsing must parse JSON payloads when enabled, escape tooltip HTML, fall back to plain text on JSON parse failure, collapse output matching the configured collapse condition, and mark long text as scrollable.
- [x] Timer digit parsing must preserve two-digit minute/second groups and reject invalid timer text.
- [x] Brightness parsing must parse mixed DDC monitor listings, DDC brightness values, Apple brightness values, internal backlight paths/values, and reject invalid brightness ratios.

## How it works

- [ ] See [docs/wiki/systems/helper-utilities.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/wiki/systems/helper-utilities.md).

## Implementation inventory

- [Helpers/AdvancedMath.js](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers/AdvancedMath.js) - calculator math helpers and formatted output.
- [Helpers/BrightnessParsing.js](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers/BrightnessParsing.js) - DDC, Apple, and internal-backlight parsing helpers.
- [Helpers/ColorList.js](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers/ColorList.js) - named color list.
- [Helpers/ColorsConvert.js](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers/ColorsConvert.js) - color conversion and derived color helpers.
- [Helpers/CustomButtonContent.js](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers/CustomButtonContent.js) - custom button dynamic content parsing.
- [Helpers/Debug.js](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers/Debug.js) - debug stringification helpers.
- [Helpers/FuzzySort.js](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers/FuzzySort.js) - fuzzy matching helper.
- [Helpers/QtObj2JS.js](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers/QtObj2JS.js) - Qt object to plain JS conversion.
- [Helpers/TextFormatter.js](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers/TextFormatter.js) - rich text display escaping and wrapping.
- [Helpers/ThemeIconResolver.js](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers/ThemeIconResolver.js) - theme icon fallback resolution.
- [Helpers/TimerDigits.js](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers/TimerDigits.js) - timer digit parsing.
- [Helpers/sha256.js](/syncthing/Sync/Projects/apps/noctalia-shell/Helpers/sha256.js) - SHA-256 hashing.

## Tests asserting this spec

- [Tests/helpers.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/helpers.test.js)

## Known gaps (current cycle)

- [ ] Split helper contracts into feature-specific specs when a helper grows behavior beyond shared utility scope.

## Out of scope

- Brightness service orchestration is covered by [docs/specs/brightness.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/brightness.md).
- Icon font and desktop-entry icon behavior is covered by [docs/specs/icons.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/icons.md).
- Custom button widget behavior is covered by [docs/specs/custom-button.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/custom-button.md).
