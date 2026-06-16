Fonts covers system font discovery, fontconfig monospace detection, font classification, model loading, fallback insertion, and font search. Runtime source lives mainly in `Services/System/FontService.qml`; implementation notes belong in [docs/wiki/systems/fonts.md](../wiki/systems/fonts.md).

## What it must do

### Loading pipeline

- [x] Initialization logs service startup.
- [x] Initialization starts fontconfig monospace loading.
- [x] Fontconfig monospace loading runs `fc-list :mono family`.
- [x] Fontconfig monospace loading starts its process.
- [x] System font loading avoids concurrent loads.
- [x] System font loading exposes loading state.
- [x] System font loading reads Qt font families.
- [x] System font loading sorts families for stable order.
- [x] System font loading clears available, monospace, and display font models plus classification cache before reload.
- [x] System font loading starts processing from the first font.
- [x] Async font processing uses bounded chunks.
- [x] Async font processing skips empty font names.
- [x] Async font processing includes every valid font in available fonts.
- [x] Async font processing classifies monospace and display fonts.
- [x] Async font processing batch-appends all model updates.
- [x] Async font processing defers remaining chunks through `Qt.callLater`.
- [x] Async font processing finalizes after the last chunk.
- [x] Finalization marks fonts loaded and clears loading state.

### Classification and cache

- [x] Monospace classification uses cached classification when present.
- [x] Monospace classification trusts fontconfig monospace data.
- [x] Monospace classification falls back to monospace naming patterns.
- [x] Monospace classification initializes cache entries as needed.
- [x] Monospace classification caches and returns the result.
- [x] Display classification uses cached display classification when present.
- [x] Display classification normalizes font names.
- [x] Display classification detects display, headline, and title naming patterns.
- [x] Display classification initializes cache entries as needed.
- [x] Display classification caches and returns the result.

### Model utilities and search

- [x] Batch append appends every item to the target model.
- [x] Sorting snapshots model rows before sorting.
- [x] Sorting orders rows by display name.
- [x] Sorting rebuilds the model through batch append.
- [x] Fallback insertion builds an existing-font lookup.
- [x] Fallback insertion only adds missing fallback fonts.
- [x] Fallback insertion appends and sorts when new fallback fonts are added.
- [x] Blank font searches return the full available-font model.
- [x] Font search normalizes queries.
- [x] Font search scans available fonts and includes matching names.
- [x] Font search returns filtered results.

## How it works

- [docs/wiki/systems/fonts.md](../wiki/systems/fonts.md)

## Implementation inventory

- `Services/System/FontService.qml` - font discovery, classification, caching, model helpers, fallback insertion, and search.
- `Modules/Panels/Settings/Tabs/GeneralTab.qml` - general settings font selectors backed by FontService models.
- `Modules/Panels/Settings/Bar/WidgetSettings/ClockSettings.qml` - clock widget font selector backed by FontService models.

## Tests asserting this spec

- `Tests/font-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for fontconfig process output parsing.
- [ ] Add executable coverage for fallback font lists applied during finalization.
- [ ] Add executable coverage for General settings font selectors.
- [ ] Add executable coverage for Clock settings font selector.

## Out of scope

- Theme color and template generation belongs in [theming.md](theming.md).
- Text rendering behavior belongs to Qt font resolution; this spec covers shell model construction and search.
