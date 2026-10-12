Notifications cover notification server lifecycle, suppression rules, replacement/deduplication behavior, progress expiry, image caching, history, and persisted read state. Runtime source lives mainly in `Services/System/NotificationService.qml`; implementation notes belong in [docs/wiki/systems/notifications.md](../wiki/systems/notifications.md).

## What it must do

### Server and image cache lifecycle

- [x] Updating the notification server destroys any previous server before creating a new one.
- [x] The notification server is created only when settings are loaded and notifications are not disabled.
- [x] Image queue processing discards completed requests, advances to the next queued source, and clears the image source when empty.
- [x] Image caching accepts only `image://` provider URLs with image ids.
- [x] Image caching derives the notification cache path, deduplicates queued ids, and starts the cacher when the queue was empty.

### Suppression

- [x] Placeholder matching trims, lowercases, and treats blank values as placeholders.
- [x] Empty placeholder notifications from unknown apps with `No summary` and blank bodies are suppressed.
- [x] Notifications with real body text or known app names are not suppressed as empty placeholders.
- [x] Terminal bell detection recognizes terminal apps with bell/beep content.
- [x] Terminal bell detection recognizes content that explicitly mentions terminal bell/beep.
- [x] Terminal notifications without bell/beep content are not terminal bell notifications.
- [x] The first terminal bell notification is allowed and records the cooldown timestamp.
- [x] Terminal bell notifications inside the cooldown are suppressed without extending the cooldown.
- [x] Terminal bell notifications after the cooldown are allowed and refresh the cooldown timestamp.
- [x] Non-terminal-bell notifications do not affect the terminal bell cooldown.

### Replacement and deduplication

- [x] Duplicate refresh locates the existing visible row and falls back to adding a new notification if the old row is gone.
- [x] Exact duplicate refresh updates actions only, rebinds the stored notification object, destroys stale watchers, ignores stale close signals, and maps the new quickshell id to the existing internal id.
- [x] Existing notification updates preserve timestamp and progress while updating display fields and timeout metadata.
- [x] Existing notification updates create a fresh watcher for the replacement notification object.
- [x] Object-change updates ignore missing active notifications, recreate data from the live object, update actions, and refresh timeout metadata.
- [x] Duplicate lookup compares content ids and returns the matching internal id.

### Cleanup and progress

- [x] Cleanup destroys active watchers, deletes active notification state, and removes every quickshell id mapping to the internal id.
- [x] Progress updates compute from current time, skip persistent/paused notifications, clamp progress at zero, avoid tiny progress writes, and animate the oldest expired notification.

### History and read state

- [x] History save serializes a fresh item list, copies rows before serializing, converts timestamps to milliseconds, writes through the JSON adapter, and logs save failures.
- [x] History load clears stale rows, tolerates missing adapter notifications, restores Date timestamps, rebuilds cached image paths for provider images, clamps invalid urgency to normal, and logs load failures.
- [x] Notification state load restores persisted `lastSeenTs` and logs load failures.
- [x] Notification state save persists `lastSeenTs` and logs save failures.
- [x] Updating last-seen state converts the current timestamp to milliseconds and persists it.
- [x] Notification history date bucketing clears time fields before range comparison.
- [x] Notification history range selection distinguishes today, yesterday, and older notifications.
- [x] Notification history current-range checks include today and all ranges, while excluding yesterday from today's range.
- [x] Notification history range counts fail closed for missing history lists, include total/all count, and tolerate invalid rows.
- [x] Notification history range count lookup uses a typed range index.
- [x] Notification history range count lookup returns zero for out-of-range indexes.
- [x] Notification history widget unread counts handle Date and numeric timestamps and count only notifications newer than `lastSeenTs`.

### Isolated popup component coverage

`Tests/notification-warnings.test.py behavior` exercises production `Modules/Notification/Notification.qml` on a private headless Cage display with inert settings, services, and widget fixtures. Assertions cover:

- Displayed app, summary, body, timestamp, parsed action label, urgency colors, and progress-width updates.
- Screen routing, hover-state pause/resume callbacks, and action identifier forwarding through direct state/signal invocation.
- Close removing history before delayed dismissal, expiry-triggered removal, invalid action JSON producing no buttons, and empty-list Loader unloading.
- Disconnection after unload, one reconnected removal handler, animated entry settling, and synthetic right-click removal preserving history.
- At `bee72465c`, nested action hover/exit and action ids stay with the owning card; dismissing the second card leaves the first intact. This exercises `ComponentBehavior: Bound` at runtime.
- All six locations (`top_right`, `bottom_left`, `top`, `bottom`, `top_left`, `bottom_right`) select the expected anchors, request 400-pixel panel/card widths and stack-relative height; the right-button/hover policy and card-sized dismissal hit area are asserted.

This is isolated component coverage, not production service expiry/deduplication, full-widget rendering, or desktop input delivery. Cage lacks layer-shell: requested geometry is tested, configured Region geometry and compositor input/cursor behavior are not. Region code is unchanged.

At `bee72465c`, targeted component static analysis drops **10→3 warnings** (previously 42→10). Standalone lint requires exit status zero and exactly three `missing-property` diagnostics from generic `Repeater.itemAt()` item types, not warning-free analysis. `lint-harness-regression` rejects an injected genuine warning.

The runner uses synthetic HOME/XDG paths and a Python audit hook denying the named real-settings path and socket connections; the synthetic audit event is rejected. It no longer reads or backs up real settings. This is not a blanket no-real-file-access proof: the reported probe caveat remains, and the Python hook does not constrain child-process file access.

### Isolated service lifecycle coverage

At `ef455de63`/`ddd0a4acf`, NotificationService midpoint subset warnings drop **15→8**; standalone production lint drops **27→14**. These are different scopes. Standalone lint accepts exactly ten unbound-owner `unqualified` accesses, two string-inference `missing-property` diagnostics, and two Quickshell metadata diagnostics (`unresolved-type`/`uncreatable-type`), with exit status zero; warnings remain unsuppressed.

`Tests/notification-service-warnings.test.py runtime` exercises production NotificationService under offscreen/software `qmltestrunner`. Four behavioral passes cover:

- Delivery ordering, duplicate/replacement identity and timestamps, live updates, stale sender/close rejection, and disposal.
- DND history-only routing, visible/history overflow, action invocation, and individual/all dismissal.
- Progress, pause/resume, expiry signal emission, and timer shutdown after explicit dismissal; expiry alone does not remove the row.
- Server recreation/disable, state/history adapter callbacks, and image-queue advancement.

Overflow cleanup retains an expected failure: removing the ListModel row loses its id before cleanup, leaving a stale quickshell-id mapping. Passing cases do not mean this bug is fixed. Delivery, storage, settings, images, and surfaces are inert fixtures. The harness checks an invisible 1×1 surface and empty mask through fixtures only. Production surface/input-region behavior is unchanged; compositor delivery and Firefox/grouped-taskbar cursor behavior remain unproven, unreproduced, and unfixed.

### Isolated history panel coverage

After `98d946beb`, targeted NotificationHistoryPanel static analysis is **30→0 warnings**; standalone lint requires no warnings and exit status zero, not project-wide warning-free acceptance.

`Tests/notification-history-warnings.test.py runtime` instantiates production `NotificationHistoryPanel.qml` under offscreen `qmltestrunner`. Two behavioral cases plus QtTest initialization/cleanup yield four reported cases:

- Preserve newest-first fixture order; bind notification ids, app/summary/body and cached-image paths; reflect summary role updates.
- Switch all/today/yesterday/older tabs, assert counts and active state, and hide excluded rows with zero height.
- Forward open/read-state and DND callbacks; dismiss the selected id, update remaining order/counts, clear history, show empty state, and count close callbacks.
- Repopulate after clear; destroy the panel, mutate the model after disposal, and recreate it in the next case.

The history ListModel and Qt Repeaters/layout are real; NotificationService, SmartPanel, settings, and display/button/image controls are fixtures. Actions invoke signals directly; this does not prove real persistence, production service integration, SmartPanel lifecycle, full widget/image rendering, desktop input, toast behavior, or whole-shell acceptance. Post-disposal mutation is bounded teardown coverage, not proof of all live-shell connection lifetimes. Firefox/grouped-taskbar cursor flicker remains unproven and unfixed.

## How it works

- [docs/wiki/systems/notifications.md](../wiki/systems/notifications.md)

## Implementation inventory

- `Services/System/NotificationService.qml` - notification server, active/history models, suppression, dedupe, image caching, progress, and persisted state.
- `Modules/Notification/Notification.qml` - per-screen notification popup, card actions, progress display, and removal lifecycle.
- `Modules/Toast/ToastOverlay.qml` - visible toast overlay.
- `Modules/Toast/ToastScreen.qml` - per-screen toast placement.
- `Modules/Panels/NotificationHistory/NotificationHistoryPanel.qml` - history panel UI.
- `Modules/Bar/Widgets/NotificationHistory.qml` - notification history bar widget and unread badge count.
- `Modules/Panels/Settings/Tabs/NotificationsTab.qml` - notification settings UI.

## Tests asserting this spec

- At `5a3d4be9d`, NotificationHistorySettings warnings drop 4→0. `Tests/Qml/AudioNotificationSettingsWarningsHarness.qml` checks show-unread-badge/hide-when-zero defaults and toggles, copy-save without source mutation, unrelated-field retention, and shared-dialog cancel/reopen/apply. This proves synthetic editor state, not badge rendering, notification delivery, persistence, or cursor-flicker resolution. Shared accounting and isolation: [testing](testing.md#audionotification-settings-isolated-runtime).

- `Tests/bar-status-warnings.test.py behavior` adds two production bar-widget cases at `c14da3540`: synthetic click/context/wheel routing, DND icon updates, fixture history clearing and settings dispatch; unread timestamps, zero/badge settings, and badge Loader destruction/recreation. ListModel mutation alone is not a tested reactive binding: the case advances `lastSeenTs`. This is separate from history-panel coverage and proves neither notification persistence/delivery nor toast/input-region flicker resolution. Cohort lint and isolation: [testing](testing.md#bar-status-cohort).

- `Tests/notification-warnings.test.py` (`lint`, `behavior`, `lint-harness`, and injected-warning `lint-harness-regression`, standalone).
- `Tests/notification-history-warnings.test.py` (`lint` and `runtime`, standalone).
- `Tests/notification-service-warnings.test.py` (`lint` and `runtime`, standalone); [service lifecycle coverage](#isolated-service-lifecycle-coverage).
- `Tests/root-service-warnings.test.py behavior` / `Tests/Qml/RootServiceHarness.qml` — production NotificationService saves/reloads a concrete history row through fixture FileView/JsonAdapter state, restores its Date timestamp, updates an active ListModel row through the real progress timer, stops that timer after clearing, and advances/clears the image queue. One of five behavioral cases at `8b1de9d34`; notification delivery, file writes, settings, and surfaces are fixtures. This does not prove expiry, deduplication, image rendering, real persistence, or input regions. Root-only lint retains seventeen `unqualified`, six `block-scope-var-declaration`, two `missing-property`, one `unresolved-type`, and one `uncreatable-type` warnings. Cohort gates: [testing](testing.md#root-service-cohort).
- `Tests/notification-service-gap-guards.test.js`
- `Tests/shell-state-consumer-roundtrip.test.js`
- `Tests/notification-history-panel-guards.test.js`
- `Tests/widget-helper-guards.test.js`
- `Tests/qml-runtime-guards.test.js`

## Known gaps (current cycle)

- [ ] Fix retained overflow cleanup failure; isolated service coverage exercises replacement and expiry signaling, but not production delivery or popup-driven expiry removal.
- [ ] Add spec coverage for notification settings UI contracts.
- [ ] Resolve the three remaining generic `itemAt()` popup type diagnostics; this slice does not establish zero warnings.
- [ ] Reproduce and fix Firefox/grouped-taskbar cursor flicker triggered per notification. It has **not been reproduced or fixed** by this slice; toast/notification layer input-region behavior is untouched, and the isolated test provides no desktop input-delivery proof.

## Out of scope

- Toast command helpers belong in a separate toast spec.
- Power profile behavior is covered by the power profile spec when extracted.
