<h1 align="center">Noir Browser</h1>

<p align="center">A personal, heavily customized Firefox skin — a fork of <a href="https://github.com/greeeen-dev/natsumi-browser">Natsumi Browser</a>.</p>

> **Noir Browser is not a standalone browser.** It is a `userChrome.css` / `userContent.css`
> skin plus an optional set of privileged JS modules, applied on top of Firefox (140+) or a
> compatible fork. It is based on Natsumi Browser 6.12.4 and remains GPLv3.

## Highlights

- **Reimagined design, fully customizable** — 9 built-in themes plus a custom theme builder,
  11 accent colors, translucency options, font settings and three icon packs (Default, Lucide,
  Fluent).
- **10 tab designs** — Blade (default), Origin, Curve, Fusion, Material, Hexagonal, Classic,
  Bubble, Clicky and Neutron, plus dedicated pinned-tab styles.
- **Layouts** — Single Toolbar, Compact Mode (toolbar/sidebar autohide), top/bottom toolbars and
  status bar integration.
- **URL bar and findbar** — floating/compact URL bar, context-aware colors, redesigned findbar.
- **Miniplayer** — control media from the sidebar, with artwork and optional scroll view.
- **Glimpse** — preview tabs with a floating overlay, multi-preview and chaining.
- **Picture-in-Picture** — restyled controls, scroll-to-move, zoom gestures, material presets.
- **PDF viewer** — modernized look with compact (autohide) modes.
- **Built-in page styling** — Firefox home, error pages, add-ons manager, about pages and a
  redesigned preferences page.
- **Keyboard shortcuts** — full rebinding with conflict handling policies.
- **Settings UI** — "Customize Noir", "Keyboard Shortcuts" and "About Noir" panes, with Chinese
  localization available.
- **Startup experience** — optional startup animation (simple or nostalgic), startup sound and a
  customizable startup icon.
- **Bento** — export/import your configuration as a `.nbto` bundle.
- **Auto-update** — version checks against manifests hosted in this repository, with one-click
  installs (full version only).

Floorp-specific integrations (workspaces, split view, panel sidebar, command palette, web apps,
gestures) and Waterfox's status bar are included but only active on those browsers.

## Installation

### Option A — development install (recommended while hacking on Noir)

Symlink the repository into a Firefox profile; edits are live after a restart. No root required
for the CSS part.

```bash
installer/dev-install.sh --profile ~/.mozilla/firefox/<profile>
```

For the JS features (Miniplayer, Glimpse, settings panes, updater…), clone
[fx-autoconfig](https://github.com/greeeen-dev/fx-autoconfig) and rerun with `--append`:

```bash
git clone --depth 1 https://github.com/greeeen-dev/fx-autoconfig /tmp/fx-autoconfig
installer/dev-install.sh --profile <profile> --append /tmp/fx-autoconfig
```

The script prints the two `sudo cp` commands for the browser install directory (fx-autoconfig
program files), plus the `about:config` switch that the settings page needs. See
[`installer/README.md`](installer/README.md) for details.

### Option B — release installer

Every tagged release ships an installer for macOS/Linux (Python/Nuitka) and Windows (batch).
The installer downloads the matching release from GitHub, so it only works after this repository
is published and the version is tagged.

```bash
python3 installer/installer.py            # install (interactive)
python3 installer/installer.py --uninstall --profile <profile>   # uninstall
```

### Option C — manual CSS-only install

Copy `noir/`, `noir-config.css`, `userChrome.css` and `userContent.css` into your profile's
`chrome/` folder. This keeps the styling but loses every JS-backed feature (see
[KNOWN-ISSUES](docs/KNOWN-ISSUES.md#css-only-installs)).

### Requirements

- Firefox 140+ or a compatible fork (Floorp recommended upstream; Zen and Midori are
  intentionally unsupported).
- `toolkit.legacyUserProfileCustomizations.stylesheets = true` in `about:config`.
- Full version: fx-autoconfig plus `userChromeJS.persistent_domcontent_callback = true`.
- Flatpak: the program directory is read-only, so the fx-autoconfig program files must be
  installed manually.

## Configuration

Almost everything is exposed in **Settings → Customize Noir** when the full version is installed.
Under the hood all options are `about:config` prefs, and they keep the upstream `natsumi.*`
namespace — the internal prefix was deliberately not renamed, so existing documentation and
settings remain valid.

Common options:

| Pref | Purpose |
|---|---|
| `natsumi.theme.type` | Theme (`default`, `gradient`, `oled`, `lucid`, `custom`, …) |
| `natsumi.theme.accent-color` | Accent color preset |
| `natsumi.tabs.type` | Tab design (`blade`, `origin`, `curve`, `fusion`, …) |
| `natsumi.theme.single-toolbar` | Single Toolbar layout |
| `natsumi.theme.compact-style` | Compact Mode variant |
| `natsumi.theme.icons` | Icon pack (`default`, `lucide`, `fluent`) |
| `natsumi.urlbar.do-not-float` | Disable the floating URL bar |
| `natsumi.updater.disabled` | Disable the auto-updater |
| `natsumi.i18n.language` | Settings UI language (`auto`, `en`, `zh-CN`) |

The complete list is documented in [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md).
`noir-config.css` holds user-tunable CSS values (accent color, home background).

## Updates

Full installs check `<repo>/main/updates/<branch>.json` at startup and offer the new release for
one-click installation. Manifests are generated by `release-scripts/write_manifest.py` and
committed by the release workflow — see [`docs/RELEASING.md`](docs/RELEASING.md).

Development installs should keep the updater disabled (`natsumi.updater.disabled = true`),
otherwise a published update replaces the `noir/` symlink with a release copy.

## Development

| Path | Contents |
|---|---|
| `noir/` | The skin: `noir.css` (browser UI entrypoint), `noir-pages.css` (content pages), `modules/`, `global/`, `icons/`, `scripts/` |
| `noir-config.css` | User-tunable CSS values |
| `userChrome.css` / `userContent.css` | Loaders only |
| `installer/` | Installer/uninstaller, `dev-install.sh`, regression tests |
| `updates/` | Update manifests (`<branch>.json`) |
| `release-scripts/` | Version checks, manifest writer, i18n checker |

```bash
python3 installer/test_installer.py     # installer/uninstaller regression suite
python3 release-scripts/check_i18n.py   # translation coverage
python3 release-scripts/check_version.py main
```

Contributor/agent context lives in [`AGENTS.md`](AGENTS.md).

## Troubleshooting

- **URL bar blur is missing** — enable `layout.css.backdrop-filter.enabled` and
  `layout.css.backdrop-filter.force-enabled`, and use hardware acceleration / WebRender.
- **No "Customize Noir" in Settings** — fx-autoconfig is not loaded; check
  `userChromeJS.persistent_domcontent_callback = true` and that the program files exist.
- **CSS changes don't apply** — restart the browser; if needed, clear the startup cache from
  `about:support`.
- **IME input interrupts the floating URL bar** — Firefox must keep the results panel open during
  composition; Noir enables `browser.urlbar.keepPanelOpenDuringImeComposition` once. See
  [KNOWN-ISSUES](docs/KNOWN-ISSUES.md#ime-composition-and-the-floating-url-bar).

## License and credits

Noir Browser is licensed under the **GNU General Public License v3** (see [`LICENSE`](LICENSE)).
It is a fork of [Natsumi Browser](https://github.com/greeeen-dev/natsumi-browser) by Green
(@greeeen-dev); the original copyright notices are kept in every file. See
[`NOTICE`](NOTICE) for attribution and modification details.

Third-party components and their licenses:

- [fx-autoconfig](https://github.com/MrOtherGuy/fx-autoconfig) (MPL-2.0) — privileged JS loader;
  program/profile files are bundled by the installer.
- [Lucide](https://lucide.dev) and [Microsoft Fluent UI](https://github.com/microsoft/fluentui-system-icons)
  icon sets — see the README/LICENSE files under `noir/icons/`.
- [Borealis](https://ico.bukvic.net/main/borealis/) sound theme (GPLv3, via
  MX-Linux/mx-sound-theme-borealis) — startup/welcome sounds.

See the upstream repository and the license headers for the full attribution list.
