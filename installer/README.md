# Noir Browser installer

Two ways to put Noir into a browser profile:

| Tool | Use it for | Downloads from |
|---|---|---|
| `dev-install.sh` | development (symlink, edits live after restart) | nothing (uses this repo) |
| `installer.py` | release install/uninstall (the binary shipped in releases for macOS, Linux and Windows) | GitHub tag archives |

## dev-install.sh

```bash
installer/dev-install.sh --profile <profile-dir>              # CSS-only dev setup
installer/dev-install.sh --profile <dir> --clean              # remove the symlinks
installer/dev-install.sh --profile <dir> --append <fx-autoconfig-dir>
```

- Symlinks `noir/`, `noir-config.css`, `userChrome.css`, `userContent.css` into
  `<profile>/chrome/`. Edits in this repo are picked up on the next browser restart.
- `--append` copies `profile/chrome/{utils,CSS,resources}` from an
  [fx-autoconfig](https://github.com/greeeen-dev/fx-autoconfig) checkout, writes
  `chrome/utils/chrome.manifest` with `../noir/` mappings, and prints the two `sudo cp`
  commands for the program files.
- Keep `natsumi.updater.disabled = true` while developing: a published update would replace the
  `noir/` symlink with a release copy.

## installer.py

The release installer is interactive and modifies real browser installs.

```bash
python3 installer/installer.py                  # menu: install / uninstall
python3 installer/installer.py --uninstall --profile <profile> \
    [--install-path <browser dir>] [--full] [--yes] [--dry-run] [--clean-prefs]
```

- Detects Firefox, Floorp, Waterfox, Librewolf and Glide profiles. Installation downloads the
  `rinne05/noir-browser` tag matching the version in `installer/installer.json`, so it only works
  once that release exists.
- Requires root/administrator to place the fx-autoconfig program files
  (`<browser>/config.js`, `<browser>/defaults/pref/config-prefs.js`); profile files need no root.
- Uninstall modes:
  - default (Noir only): removes `chrome/noir*`, loaders and config, restores fx-autoconfig's own
    `chrome.manifest`, keeps fx-autoconfig and other mods working.
  - `--full`: additionally removes fx-autoconfig program/profile files and installs the
    `chrome.manifest` cleanup.
- Safety behaviour: restores `userChrome.css`/`userContent.css` from `.bak` files created by the
  installer, backs up customized loaders as `.noir-backup` instead of deleting them, only removes
  `chrome/JS/` copies that are byte-identical to installed scripts, and removes dev symlinks
  without touching their targets. Permission failures are reported per item with a sudo hint.
- `--clean-prefs` rewrites `prefs.js` (backup `prefs.js.noir-backup`), stripping `natsumi.*` and
  (with `--full`) `userChromeJS.*`. Firefox must be closed.
- `--dry-run` prints the full plan without changing anything.

### Install manifest and uninstall contract

The installer writes `chrome/.noir-install.json` recording every installed path, the
fx-autoconfig pre-existence flags, created `.bak` files and `chrome/JS/` copies. The uninstaller
trusts it, so when the installer starts copying something new, append the target to
`manifest_profile_paths` / `manifest_external_paths` / `manifest_js_copies` in `main()` and the
uninstaller needs no change.

New runtime artifacts in the profile root or `chrome/` must use the `noir-*` prefix; the
uninstaller discovers unknown such entries and backs them up as `.noir-backup` (or deletes empty
directories). Legacy `natsumi-*` artifacts and the old `natsumi/` layout are still cleaned.

### Regression tests

```bash
pip install -r installer/requirements.txt   # requests, certifi
python3 installer/test_installer.py         # 110 checks, including a full offline install→uninstall round trip
```

The suite uses temporary fixtures only (it patches downloads and never touches a real browser).

## Windows

Windows releases ship `noir-installer-windows.exe`, built from `installer.py` with Nuitka. It
supports the same interactive install/uninstall flow, install manifest and safety behaviour as the
macOS/Linux binaries. Because fx-autoconfig writes `config.js` and `defaults/pref` into the browser
install folder, the executable requests Administrator rights through its UAC manifest; accept the
prompt. Profile files still go to the selected profile's `chrome/` folder.

To build it locally on Windows:

```powershell
pip install nuitka -r installer/requirements.txt
python -m nuitka --onefile --windows-uac-admin `
  --include-data-files="installer/installer.json=installer.json" `
  installer/installer.py
```

Or run the **Build (no release)** workflow and download the `noir-installer-windows` artifact.

`windows-installer.bat` is the legacy Git-based script kept for source checkouts. It installs from
the `main`/`dev` branches, has no uninstall or install manifest, and is no longer shipped in
releases.

## Notes

- Temporary download directory: `.noir-installer` (removed after the run).
- Flatpak browsers need a manual install because the program directory is read-only.
- Release builds are produced by `.github/workflows/build.yml` / `release.yml` with Nuitka; see
  `docs/RELEASING.md`.
