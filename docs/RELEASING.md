# Releasing Noir Browser

Update manifests are hosted in this repository (`updates/<branch>.json`), so there is no separate
updates repository and no deploy key.

## 1. Bump the version (three files, must match)

| File | Field |
|---|---|
| `noir/version.json` | `version` (and optionally `codename`; `branch` = manifest name: `stable`/`rc`/`beta`/`alpha`) |
| `installer/installer.json` | `package.version` (plus `version_rc`/`version_beta`/`version_alpha` if used) |
| `theme.json` | `version` (Sine) |

```bash
python3 release-scripts/check_version.py main   # must print "Version matches!"
```

## 2. Commit and tag

```bash
git add -A && git commit -m "release: v6.12.4"
git tag v6.12.4
git push origin main --tags
```

The tag **must** be `v<version>` — the installer and manifest writer derive the archive URL from
it.

## 3. Run the workflow from the tag

Actions → **Build & release** → Run workflow → select tag `v6.12.4`.

1. `check-version` verifies the three version files.
2. `build-installer` builds the macOS (arm64 + Intel), Linux and Windows artifacts with Nuitka.
   The Windows artifact is `noir-installer-windows.exe`; the legacy batch is not shipped.
3. `release` creates a **draft** GitHub release with the artifacts.
4. `publish` (environment-gated, environment name = tag) runs `release-scripts/write_manifest.py`,
   which downloads the tag archive, computes its SHA-256 and writes `updates/<branch>.json`,
   then commits that file to `main` with the built-in token.

`Publish only` can be run later to regenerate the manifest without rebuilding.

## 4. Verify

```bash
curl -s https://raw.githubusercontent.com/rinne05/noir-browser/main/updates/stable.json
```

- `version` / `tag` must match the release.
- `hash` must equal the archive hash; re-check locally with
  `python3 release-scripts/write_manifest.py --repo rinne05/noir-browser --dry-run`
  (add `--force` to republish an unchanged version).
- A client on the previous version should show the update notification; installing it verifies
  the extract glob `noir-browser-*/noir/*` and the replacement of `chrome/noir`.

## Notes

- The GitHub release being a draft does not block updates: clients download the tag archive and
  the manifest, not the release page. Publish the release manually when ready.
- `raw.githubusercontent.com` caches for a few minutes; a fresh manifest may take a few minutes to
  appear.
- Manifests cannot live inside the released tag (the archive hash only exists after the tag is
  pushed), which is why they are committed to `main` afterwards.
- If `main` is branch-protected, allow GitHub Actions to push (or use a PAT).
- Don't bump the version on `main` for the next cycle until the publish job has run; the manifest
  is generated from `main`'s `noir/version.json`.
