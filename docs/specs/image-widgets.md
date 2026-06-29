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

- `Tests/image-widget-resource-guards.test.js`
- `Tests/source-coverage.test.js`
