Toast covers lightweight transient messages, toast command helpers, queue management, and per-screen toast activation. Runtime source lives mainly in `Services/UI/ToastService.qml` and `Modules/Toast/ToastScreen.qml`; implementation notes belong in [docs/wiki/systems/toast.md](../wiki/systems/toast.md).

## What it must do

### Service helpers

- [x] Notice toasts forward message, description, icon, notice type, and a default duration of 3000 ms.
- [x] Warning toasts forward message, description, an empty icon, warning type, and caller-provided duration.
- [x] Error toasts forward message, description, an empty icon, error type, and a default duration of 6000 ms.
- [x] Toast service helper APIs type required message inputs while keeping optional defaults flexible.

### Queueing

- [x] Enqueuing a toast appends it to the message queue and processes the queue.
- [x] Enqueuing into a full queue drops the oldest toast before appending the newest toast.
- [x] Enqueuing while replacement mode is active and a toast is visible replaces the visible toast, stops the hide timer, hides the visible item, marks no toast visible, and restarts the quick-switch timer.
- [x] Replacement-mode enqueueing does not process the queue immediately while the visible toast is being switched.

### Per-screen activation

- [x] Queue processing ignores empty queues.
- [x] Queue processing leaves queued messages untouched when a toast is already visible.
- [x] Queue processing activates the toast loader with the next toast, marks a toast visible, and removes the activated toast from the queue.

### Visible toast item

- [x] Showing a visible toast stops pending hide timers, stores message/description/icon/type/duration, applies default optional fields, shows the toast, restores opacity/scale, and restarts the hide timer.
- [x] Showing a visible toast types the required message input while keeping optional display inputs flexible.
- [x] Hiding a visible toast stops the hide timer, fades/scales out, and restarts the hide animation.
- [x] Immediate hide stops timers, fades/scales out, clears visibility, and emits the hidden signal.

## How it works

- [docs/wiki/systems/toast.md](../wiki/systems/toast.md)

## Implementation inventory

- `Services/UI/ToastService.qml` - notice, warning, and error helper APIs that emit toast notifications.
- `Modules/Toast/ToastScreen.qml` - per-screen queue, replacement, quick-switch, loader activation, and hidden-toast handling.
- `Modules/Toast/ToastOverlay.qml` - overlay that instantiates a toast screen for each shell screen.
- `Modules/Toast/SimpleToast.qml` - visible toast item, display fields, timers, show/hide animation, and click-to-hide behavior.

## Tests asserting this spec

- `Tests/toast-service-guards.test.js`
- `Tests/toast-screen-guards.test.js`
- `Tests/simple-toast-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for `ToastScreen.onToastHidden` cleanup and queue continuation.
- [ ] Add UI-level coverage for toast icon, message, description, type color, and click-to-hide rendering.
- [ ] Add multi-screen coverage for `ToastOverlay` screen delegation.

## Out of scope

- Notification history, suppression, and terminal bell cooldown behavior are covered by [docs/specs/notifications.md](notifications.md).
- Feature-specific toast triggers belong in the specs for those features.
