Image widgets cover shared rounded-image and cached-thumbnail resource behavior. Runtime source lives mainly in `Widgets/NImageRounded.qml` and `Widgets/NImageCached.qml`.

## What it must do

### Rounded images

- [x] Rounded images load their backing `Image` only while visible, non-fallback, sized, and given a source path.
- [x] Rounded images clear the backing image source when hidden or fallback-only.
- [x] Rounded images request decode size from rendered size and device pixel ratio.
- [x] Rounded images avoid mipmap allocation for small rounded UI images.
- [x] Rounded image shaders instantiate only while image resources are needed.

### Cached thumbnails

- [x] Cached thumbnails load images only while visible, sized, and given a source path.
- [x] Cached thumbnails clear their source when not loadable.
- [x] Cached thumbnails avoid hidden decode targets.
- [x] Cached thumbnails centralize cache/original source transitions.
- [x] Cached thumbnails run `grabToImage` only for visible ready originals in a visible window.

## Implementation inventory

- `Widgets/NImageRounded.qml` - rounded image/fallback icon widget.
- `Widgets/NImageCached.qml` - cached thumbnail image widget.

## Tests asserting this spec

- `Tests/image-shadow-warnings.test.py` — isolated rounded-image source/visibility/geometry and shadow owner/source lifecycle; no shader-pixel proof.

- `Tests/image-widget-resource-guards.test.js`
- `Tests/source-coverage.test.js`

### Rounded image and shadow isolated evidence

- At `d0b363b73`/`cb32accad`, dedicated lint reports NDropShadow 7→0 and NImageRounded 7→0 `unqualified` warnings. Two unused-import informational notices remain; this is not whole-shell warning clearance.
- `Tests/Qml/ImageShadowWarningsHarness.qml` has seven behavioral cases (nine reported passes including QtTest init/cleanup): image geometry/decode resizing and zero-size recovery; source/visibility/fallback/status transitions; rounded-effect geometry and Loader recreation; shadow source/property transitions; separate image and shadow two-instance creation-context isolation; shadow enable/settings/performance transitions. Production `Bound` components run offscreen with synthetic services.
- Reported staged-copy negative controls remove the shadow source binding or force rounded corner radius to zero; both fail. Property/lifecycle assertions do not verify shader pixels, GPU rendering, live compositor interaction, real settings persistence, or live resource use. Runner isolation and acceptance: [testing](testing.md#image-and-shadow-isolated-runtime).
