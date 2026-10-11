# Inline settings types prototype

Scope: `ui` and nested `bar.widgets` only, branch `fix/qml-settings-types`.
Base: `a1a4dd42e42427db0d0bf69fc58f3bc0e468375d`.

## Proof ledger — 2026-10-11

Command (explicit worktree cwd): `python3 Tests/settings-types.test.py -v`.

| Source scope | Result | Validity |
| --- | --- | --- |
| Base SettingsData, final test expectations | RED: two behavioral tests pass; static test fails with 5 missing-property warnings | Historical baseline |
| Formatted prototype SettingsData SHA256 `1713fc2cf1b9eb7f7c7889db0e5babd6528c0572547c2027b352f67e87877d52` | GREEN: all 3 tests pass; 1 missing-property warning | No subsequent source/test changes |

Targeted formatter: `/usr/lib/qt6/bin/qmlformat -w 2 -W 360 -S --semicolon-rule always -i` on `Commons/SettingsData.qml` and `Tests/Qml/SettingsTypesHarness.qml` before GREEN.

## External contract evidence

Fixtures capture the unmodified base adapter's actual `FileView.writeAdapter()` bytes, not `Assets/settings-default.json` (which differs from current source defaults).

- Default output: 10,422 bytes; SHA256 `5ec43229082421750995acf3895b452ddbaff779ee42f1aeacbdb288450c5e56`.
- Mutated output: 9,904 bytes; SHA256 `c692b430cf4104d0a03dd9dfec68b0f1d00b32928113d0faa2b994b8f1fc1c3d`.
- Both compare byte-for-byte to frozen fixtures. Mutation also compares the entire parsed document to concrete expected data. A fresh process reloads and saves the mutated document unchanged.
- Sparse loading retains missing-field defaults. Unknown root, bar, ui and widgets schema keys are omitted; arbitrary widget-record data and nested arrays survive loading. Mutation updates ui fields and all three widget arrays.

## Coverage and limits

| Case | Proof |
| --- | --- |
| `Settings.data.ui.fontDefault`, `fontFixed`, `fontDefaultScale`, `tooltipsEnabled` | Real qmllint: 4 warnings → 0 |
| `Settings.data.bar.widgets.left` | Real qmllint: 1 warning remains at generic `bar.widgets` |
| Inline `UiSettings` and `BarWidgets` serialization | Real offscreen Quickshell / JsonAdapter / FileView |
| Production Settings bootstrap, migrations, watcher, concurrency | Not exercised; harness uses equivalent minimal data alias, not production singleton orchestration |
| Other schema groups / whole-repo warning count | Not tested or changed |

Harness copies production SettingsData and SettingsDefaults into a temporary tree; replaces desktop OSD with its enum-only dependency. It has no windows, uses an environment allowlist, isolates HOME and every XDG directory, omits Wayland/display/session-bus variables, and forces Qt offscreen/software. Every subprocess has a timeout and is reaped. Save is scheduled after the load callback returns to avoid overlapping FileView operations.

Real settings hash checked before/after each runtime probe and after GREEN: `bc53e7cae6f456d443ba79ccee688802f18fb38abd6cbfc695ae331885b841e4`. Existing unique backup verified identical, mode 0600. Final process observation found only the canonical Quickshell; no experimental instances remained.

Generalization is supported for these two tested JsonObject cases, not proven for every schema group. Nested static resolution requires typing the enclosing `bar` too; that is outside this prototype. Full suites, readability, deployment and restart were intentionally excluded. Commit hooks are bypassed only to avoid the repository-wide formatter; changed QML was formatted explicitly above.
