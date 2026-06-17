Logger covers shared QML log formatting, level routing, debug gating, stack capture, and call-stack printing. Runtime source lives in `Commons/Logger.qml`; implementation notes belong in [docs/wiki/systems/logger.md](../wiki/systems/logger.md).

## What it must do

### Message formatting

- [x] Log formatting timestamps every message.
- [x] Log formatting treats the first argument as a module label when multiple arguments are present.
- [x] Module labels are clamped to 14 characters and padded to a fixed width.
- [x] Formatted messages colorize timestamps and module labels.
- [x] Message arguments are joined with spaces.
- [x] Module-less messages are formatted without a module label.
- [x] Log formatting produces concrete console strings with fake timestamps and fake console sinks.

### Level routing

- [x] Debug logging formats and writes to `console.debug` only when debug mode is enabled.
- [x] Debug logging writes nothing when debug mode is disabled.
- [x] Info logging formats and writes to `console.info`.
- [x] Warning logging formats and writes to `console.warn`.
- [x] Error logging formats and writes to `console.error`.

### Stack traces

- [x] Stack trace capture returns JavaScript stack text from an Error object.
- [x] Call-stack logging captures a stack trace and prints a visible header.
- [x] Call-stack logging splits stack text into lines and iterates every line.
- [x] Call-stack logging trims stack lines and logs only non-empty lines.
- [x] Call-stack logging prints a closing separator.
- [x] Call-stack logging filters blank stack lines and formats non-empty lines with a `- ` prefix.

## How it works

- [docs/wiki/systems/logger.md](../wiki/systems/logger.md)

## Implementation inventory

- `Commons/Logger.qml` - shared logging singleton, formatting, debug/info/warn/error routing, stack capture, and call-stack output.

## Tests asserting this spec

- `Tests/logger-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)


## Out of scope

- Feature-specific log messages belong in the specs for those features.
