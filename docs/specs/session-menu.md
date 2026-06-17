Session Menu covers the power/session action panel, countdown confirmation behavior, keyboard navigation, action dispatch, and settings-tab persistence for enabled actions. Runtime source lives mainly in `Modules/Panels/SessionMenu/SessionMenu.qml` and `Modules/Panels/Settings/Tabs/SessionMenuTab.qml`; implementation notes belong in [docs/wiki/systems/session-menu.md](../wiki/systems/session-menu.md).

## What it must do

### Action and countdown flow

- [x] `startTimer` and `executeAction` action parameters are typed as strings.
- [x] Starting an action executes immediately when global countdown is disabled.
- [x] Starting an action finds the selected power option by action id.
- [x] Starting an action executes immediately when that option disables countdown.
- [x] A second click on the pending action confirms immediately.
- [x] Starting a countdown sets pending action, remaining time, active state, and starts the countdown timer.
- [x] Countdown timer ticks subtract the timer interval and execute the pending action when time expires.
- [x] Canceling countdown clears active state, pending action, remaining time, and stops the timer.

### Action dispatch

- [x] Executing an action stops countdown before dispatching.
- [x] Lock action activates the lock screen when available and inactive.
- [x] Suspend action honors lock-on-suspend by choosing lock-and-suspend or suspend.
- [x] Hibernate, reboot, logout, and shutdown actions delegate to CompositorService.
- [x] Executing an action clears timer state and closes the panel after dispatch.
- [x] IPC lock-and-suspend delegates through CompositorService.

### Navigation

- [x] Next and previous selection wrap through available power options.
- [x] First selection sets index zero.
- [x] Last selection selects the final option and clamps empty option lists to zero.
- [x] Activation starts the selected option action and ignores missing selected options.
- [x] Power option delegates type icon, title, action, shutdown, and pending roles instead of using dynamic `modelData.*` reads.

### Settings tab

- [x] Saving entries persists action id, enabled state, and countdown-enabled state.
- [x] Missing countdown settings default to enabled.
- [x] Updating an entry copies the changed model item before persisting.
- [x] Updating an entry types the entry index while keeping the patch object input flexible.
- [x] Updating an entry preserves untouched model entries.
- [x] Reordering entries moves the item and persists the new order.
- [x] Reordering entries types both source and destination indexes.
- [x] Session Menu tab entry delegates type scalar roles, expose a strict readonly enabled alias, and avoid `Item.enabled` role collisions.

## How it works

- [docs/wiki/systems/session-menu.md](../wiki/systems/session-menu.md)

## Implementation inventory

- `Modules/Panels/SessionMenu/SessionMenu.qml` - SmartPanel power/session action UI, countdown behavior, keyboard navigation, and action dispatch.
- `Modules/Panels/Settings/Tabs/SessionMenuTab.qml` - settings UI helpers for enabled actions, countdown flags, and ordering.
- `Services/Compositor/CompositorService.qml` - action backend for suspend, hibernate, reboot, logout, shutdown, and lock/suspend.
- `Services/UI/PanelService.qml` - lock screen activation used by the lock action.
- `Services/Control/IPCService.qml` - session menu IPC command routing.
- `Assets/settings-default.json` - default Session Menu action list and countdown settings.

## Tests asserting this spec

- `Tests/session-menu-guards.test.js`
- `Tests/session-menu-tab-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/qml-runtime-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for rendered pending/selected button state.
- [ ] Add executable coverage for per-action compositor failure feedback.
- [ ] Add executable coverage for Session Menu IPC open/toggle behavior.

## Out of scope

- Backend compositor action implementation belongs in [compositor.md](compositor.md).
- Lock screen rendering belongs in a future lock-screen spec.
