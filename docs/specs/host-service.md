Host Service covers host identity and operating-system metadata exposed to shell surfaces. Runtime source lives mainly in `Services/System/HostService.qml`; implementation notes belong in [docs/wiki/systems/host-service.md](../wiki/systems/host-service.md).

## What it must do

### OS logo resolution

- [x] Logo candidate building rejects blank names.
- [x] Logo candidate building rejects path-like and dot-prefixed names.
- [x] Logo candidate building includes pixmaps SVG and PNG paths before icon-theme paths.
- [x] Logo candidate building includes hicolor scalable and raster app-icon paths.
- [x] Logo candidate building includes NixOS current-system hicolor app-icon paths.
- [x] Logo candidate building includes common generic `/usr/share/icons` fallbacks.
- [x] Logo resolution skips invalid names without mutating or starting the probe process.
- [x] Logo resolution builds a shell file-existence probe over the candidate list and starts it for valid names.

## How it works

- [docs/wiki/systems/host-service.md](../wiki/systems/host-service.md)

## Implementation inventory

- `Services/System/HostService.qml` - host display name, OS release metadata, logo lookup, readiness, and NixOS detection.
- `shell.qml` - setup wizard gating consumes host readiness and NixOS state.
- `Modules/Panels/SetupWizard/SetupWizard.qml` - setup wizard surface gated by host state through `shell.qml`.

## Tests asserting this spec

- `Tests/host-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for `/etc/os-release` parsing, `isReady`, `isNixOS`, and logo-name handoff.
- [ ] Add executable coverage for probe process exit handling and `osLogo` URL assignment.
- [ ] Add executable coverage for `displayName` precedence across explicit real name, getent real name, `$USER`, and fallback.

## Out of scope

- Setup wizard timer and panel behavior belongs in a future setup/onboarding spec.
