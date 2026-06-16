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

## How it works

- [docs/wiki/systems/notifications.md](../wiki/systems/notifications.md)

## Implementation inventory

- `Services/System/NotificationService.qml` - notification server, active/history models, suppression, dedupe, image caching, progress, and persisted state.
- `Modules/Toast/ToastOverlay.qml` - visible toast overlay.
- `Modules/Toast/ToastScreen.qml` - per-screen toast placement.
- `Modules/Panels/NotificationHistory/NotificationHistoryPanel.qml` - history panel UI.
- `Modules/Panels/Settings/Tabs/NotificationsTab.qml` - notification settings UI.

## Tests asserting this spec

- `Tests/notification-service-gap-guards.test.js`
- `Tests/notification-history-panel-guards.test.js`
- `Tests/qml-runtime-guards.test.js`

## Known gaps (current cycle)

- [ ] Add executable tests for active-list replacement and progress expiry with a fake `ListModel`.
- [ ] Add behavior tests for notification history panel filtering/actions.
- [ ] Add spec coverage for notification settings UI contracts.

## Out of scope

- Toast command helpers belong in a separate toast spec.
- Power profile behavior is covered by the power profile spec when extracted.
