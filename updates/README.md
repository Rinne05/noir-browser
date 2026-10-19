# Update manifests

Written by `release-scripts/write_manifest.py` (run by the release/publish
workflows after a tag is pushed, or by hand on `main`). The client updater
(`noir/scripts/updater.uc.mjs`) fetches
`https://raw.githubusercontent.com/rinne05/noir-browser/main/updates/<branch>.json`.

The manifest cannot live inside the released tag itself: the archive hash only
exists after the tag is pushed and GitHub generates the zip.

| Field | Meaning |
|---|---|
| `version` | version from `noir/version.json` |
| `tag` | GitHub tag whose archive is downloaded |
| `hash` | SHA-256 of the tag archive zip (verified by the client before install) |
| `releasedAt` | unix timestamp, used to detect newer releases |

One file per update channel, named after the `branch` field of
`noir/version.json` (`stable`, `rc`, `beta`, `alpha`).
