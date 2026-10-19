# AGENTS.md

Noir Browser: a personal GPLv3 fork of [Natsumi Browser](https://github.com/greeeen-dev/natsumi-browser),
a skin/mod for Firefox-based browsers. The repo root is meant to *be* the profile `chrome/`
folder. No build step, no package manager, no linter; the only automated checks are the Python
scripts listed below.

**Working agreement: implement and verify, then stop. Do not commit (or rewrite history) until
the user explicitly confirms.**

## Repo map

- `noir/` — the skin. `noir/noir.css` is the browser-UI entrypoint and import manifest
  (config → preload → global → modules → fork modules → postload). `noir/noir-pages.css` is the
  content-pages entrypoint for `noir/content/`.
- `noir-config.css` — user-tunable values (accent color, home background). Not a place for
  feature defaults.
- `noir/modules/injected/*.css` — injected at runtime into dialogs/popups by
  `scripts/css-injector.uc.mjs`; not part of the import chain.
- `noir/scripts/*.uc.mjs` — privileged scripts (fx-autoconfig, `// ==UserScript==` headers,
  `@include main` = browser window). `*.sys.mjs` are modules; `actors/` holds JSWindowActors.
- `installer/` — installer/uninstaller (`installer.py`), `dev-install.sh`, regression tests,
  Windows batch. `updates/` — update manifests. `release-scripts/` — version/manifest/i18n checks.
- Docs: `README.md` (users), `docs/CONFIGURATION.md`, `installer/README.md`, `docs/RELEASING.md`,
  `docs/KNOWN-ISSUES.md`.

## Invariants

- **Identity**: display name is "Noir (Browser)". Shipped paths are `noir/`, `noir/noir.css`,
  `noir/noir-pages.css`, `noir-config.css`. Never rename the internal identifiers — `natsumi.*`
  prefs, `--natsumi-*` CSS vars, `chrome://natsumi/` URLs, `Natsumi*` JS classes, `natsumi-*`
  ids/classes — they are load-bearing (pref data, content package). Keep all license headers.
- **Legacy compatibility**: installer, uninstaller and updater must keep handling the old
  `natsumi/` layout and `natsumi-*` runtime artifacts; new artifacts use the `noir-*` prefix.
- **Uninstall contract** (details in `installer/README.md`): `chrome/.noir-install.json` records
  what the installer created — append new copy steps to `manifest_profile_paths` /
  `manifest_external_paths` / `manifest_js_copies`. Loader files must keep importing
  `noir/noir.css` / `noir/noir-pages.css` (legacy fragments are also matched). Prefs cleanup
  strips `natsumi.*` (plus `userChromeJS.*` in `--full`); new namespaces belong in
  `noir_pref_lines()`. Anything living entirely inside `chrome/noir/` needs no uninstall changes.
- **i18n**: `noir/scripts/i18n-zh.sys.mjs` keys are the English source strings exactly as
  displayed (whitespace collapsed). Static panes are localized by `localizeDom` at the end of
  each preferences script; dynamic strings need `t()` at the assignment site. Run
  `python3 release-scripts/check_i18n.py` after editing preferences (expect 0 missing / 0 stale).
- **CSS**: feature toggles are read in CSS via `@media -moz-pref("natsumi.x.y")`; prefs are often
  unset, so handle the unset case (`not -moz-pref(...)` = enabled by default). Fork CSS is gated
  by `natsumi.browser.type` (set by `detect-fork.uc.mjs`). Native nesting + Firefox-only
  features; generic linters produce false positives.
- **Scripts**: adding/renaming one requires the `theme.json` `scripts` map to stay in sync
  (`release-scripts/generate_scripts.py` regenerates it from UserScript headers; not run in CI).

## Workflows

- Dev install (no root for CSS): `installer/dev-install.sh --profile <profile>` symlinks
  `noir/`, `noir-config.css`, `userChrome.css`, `userContent.css` into the profile's `chrome/`.
  Restart to load; `--clean` removes the links. Full mode: clone
  `https://github.com/greeeen-dev/fx-autoconfig` and rerun with `--append <checkout>`, then apply
  the printed program-file `sudo cp` commands and set
  `userChromeJS.persistent_domcontent_callback = true`.
- **Keep `natsumi.updater.disabled = true` while developing**: when a manifest is published the
  updater replaces the `noir/` symlink with a release copy (and before then every check logs an
  unhandled rejection because no manifest exists).
- Tests: `python3 installer/test_installer.py` (needs `requests`/`certifi` from
  `installer/requirements.txt`); version check: `python3 release-scripts/check_version.py main`.
- Release: see `docs/RELEASING.md`. Update manifests live at `updates/<branch>.json` on `main`;
  the updater fetches them from `raw.githubusercontent.com/rinne05/noir-browser/main/updates` and
  verifies the SHA-256 of the tag archive before extracting `noir-browser-*/noir/*`. Repo rename →
  change the download URL and that glob together or updates install nothing.
- The floating URL bar only exists with Append and is keyed on `#urlbar[open]`. Firefox closes
  the panel during IME composition unless `browser.urlbar.keepPanelOpenDuringImeComposition` is
  true; `meow.uc.mjs` sets it once (no user value only) and the URL bar layout setting explains
  it. `urlbar.uc.mjs` runs its mutation body once per batch (not per mutation record).
- No release installer during development: `installer/installer.py` downloads a tagged archive
  from GitHub, so it only works once the repo is pushed and released.

## Gotchas

- This machine's Firefox profiles live under `~/.config/mozilla/firefox/` (XDG path), not
  `~/.mozilla/firefox/`.
- CSS-only installs lose all JS features (Miniplayer, Glimpse, settings panes, updater, …).
- If CSS fails to load, `postload.uc.mjs` warns in-page: it checks `--natsumi-postload-complete`
  from `noir/modules/postload.css`, so a silent UI usually means a broken `@import` chain.
- After CSS edits restart the browser; clear the startup cache from `about:support` if needed.
  The Browser Toolbox (`Ctrl+Shift+Alt+I`) Style Editor edits profile stylesheets live.

## Upstream sync

The pristine upstream snapshot is tagged `upstream-v6.12.4` (`git diff upstream-v6.12.4 -- <path>`
separates fork changes). To merge upstream: add `greeeen-dev/natsumi-browser` as a remote and use
`--allow-unrelated-histories`, then re-apply the Noir naming where upstream touched the same
strings.
