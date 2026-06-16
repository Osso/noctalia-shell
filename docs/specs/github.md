GitHub covers cached Noctalia GitHub metadata, contributor lists, contributor avatar caching, and About tab contributor index typing. Runtime source lives mainly in `Services/Noctalia/GitHubService.qml`; implementation notes belong in [docs/wiki/systems/github.md](../wiki/systems/github.md).

## What it must do

### Cache and fetch lifecycle

- [x] Initialization logs service startup and hydrates cached GitHub data.
- [x] Cache loading compares cache timestamps against current time and the configured update frequency.
- [x] Cache loading detects missing or expired cache data.
- [x] Cache loading publishes cached version and contributor data when present.
- [x] Cache loading refreshes stale cache data.
- [x] Fetching avoids concurrent GitHub requests.
- [x] Fetching starts both version and contributors requests.
- [x] Saving stamps cached data with the current time.
- [x] Saving ensures the cache directory exists.
- [x] Saving defers FileView writes.
- [x] Data is saved only after both version and contributors requests finish.
- [x] Resetting cache clears cached version, contributors, and timestamp, then refetches.

### Avatar metadata persistence

- [x] Metadata loading reads from the configured metadata path.
- [x] Metadata loading attaches stdout collection.
- [x] Metadata loading parses non-empty JSON.
- [x] Metadata loading populates circular avatar paths.
- [x] Metadata loading marks metadata loaded.
- [x] Metadata loading recovers from parse failures with empty metadata.
- [x] Metadata loading initializes empty metadata when file reads fail.
- [x] Metadata saving ensures the avatar cache directory exists.
- [x] Metadata saving serializes pretty JSON.
- [x] Metadata saving base64-encodes metadata before shell write.
- [x] Metadata saving decodes into the metadata path and cleans up the save process.

### Contributor avatar queue

- [x] Avatar caching ignores empty contributor lists.
- [x] Avatar caching marks the contributor set processed.
- [x] Avatar caching ensures the avatar cache directory exists.
- [x] Avatar caching rebuilds the queue.
- [x] Avatar caching processes only the top 20 contributors.
- [x] Avatar caching derives circular avatar paths by username.
- [x] Avatar caching queues new users and changed avatar URLs.
- [x] Avatar caching reuses existing cached avatars.
- [x] Avatar caching removes stale metadata and circular avatar files for removed top contributors.
- [x] Avatar caching saves metadata after cleanup.
- [x] Avatar caching either processes queued work or notifies reused cache.

### Avatar processing

- [x] Avatar processing avoids empty or concurrent work.
- [x] Avatar processing claims and dequeues one item at a time.
- [x] Avatar processing downloads to a temporary avatar path.
- [x] Avatar downloads use curl with wget fallback.
- [x] Avatar downloads report success and clean up the process.
- [x] Successful avatar downloads are rendered into circular avatars.
- [x] Failed avatar downloads release the worker and continue queue processing.
- [x] Circular rendering uses the ImageMagick resize pipeline.
- [x] Circular rendering records success from the process exit code.
- [x] Successful circular rendering updates avatar metadata with URL, cached path, and timestamp.
- [x] Successful circular rendering publishes file URLs, emits the change signal, and persists metadata.
- [x] Circular rendering removes temporary input files.
- [x] Circular rendering releases the worker, continues queue processing, destroys the conversion process, and starts conversion work.

### Types

- [x] About tab top contributor delegates declare an index role.
- [x] About tab remaining contributor delegates declare an index role.

## How it works

- [docs/wiki/systems/github.md](../wiki/systems/github.md)

## Implementation inventory

- `Services/Noctalia/GitHubService.qml` - GitHub version/contributor fetches, cache file lifecycle, avatar queueing, avatar metadata, download, and circular rendering.
- `Modules/Panels/Settings/Tabs/AboutTab.qml` - contributors UI backed by GitHubService data and cached avatar paths.
- `Assets/settings-default.json` - default settings that include About/settings surfaces using Noctalia metadata.

## Tests asserting this spec

- `Tests/github-service-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for parsing version/contributor process output.
- [ ] Add executable coverage for About tab contributor rendering and click actions.
- [ ] Add executable coverage for avatar cache metadata loaded from real fixture JSON.
- [ ] Add executable coverage for failure to run curl/wget or ImageMagick.

## Out of scope

- Color scheme repository downloads belong in [theming.md](theming.md).
- General settings panel navigation belongs in [settings.md](settings.md).
