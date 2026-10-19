# Known issues and limitations

## IME composition and the floating URL bar

**Symptom:** when typing Chinese/Japanese/Korean with an input method, the floating URL bar drops
back to its normal toolbar position mid-composition (the caret appears to jump back to the default
top address bar). English input is unaffected.

**Cause:** Firefox closes the URL bar results panel when an IME composition starts, unless
`browser.urlbar.keepPanelOpenDuringImeComposition` is true. Closing the panel removes
`#urlbar[open]`, and Noir's floating geometry is keyed on that attribute.

**Behaviour in Noir:** `meow.uc.mjs` enables the pref once, and only when you have no value for it,
so a manual `about:config` choice is respected. The settings page (Settings → Customize Noir →
URL Bar → Layout) carries a note explaining this. If you disable the pref, the collapse comes back
— including the composition interruption risk. This only affects the full (Append) install; the
CSS-only version has no floating URL bar.

## Development symlink vs. the auto-updater

`installer/dev-install.sh` symlinks `noir/` into the profile. A published update replaces that
path with a release copy, which silently ends the symlink workflow. While developing, set
`natsumi.updater.disabled = true` (also stops the console noise below until the first release).

## Update checks before the first published manifest

The updater fetches `updates/<branch>.json` from this repository. Until the repository is pushed
and a manifest is published, the request returns 404 and the updater logs an unhandled rejection
on each browser window load (it has no `.catch`). Disabling the updater removes the noise.

## CSS-only installs

Without fx-autoconfig the following are unavailable: Miniplayer, Glimpse, keyboard shortcut
manager, Single Toolbar, Compact Mode, Natsumi toolbars, theme builder/custom themes, settings
panes, welcome page, notifications, Bento, auto-updater, Floorp/Waterfox integrations, tab
animations, pinned-tab icon handling, browser/content separation and font settings. Styling,
themes, PDF viewer, URL bar/findbar looks and PiP appearance remain.

## Floorp-only and Waterfox-only features

Floorp-specific integrations (workspaces, split view, panel sidebar, command palette styling, web
apps styling, gestures, Floorp modules, tab style reset, Floorp Hub warning hiding) do nothing on
Firefox. Waterfox-specific pieces are the status bar styling/integration and its compatibility
tweaks. Both are gated by `natsumi.browser.type` and simply stay inactive elsewhere.

## Unsupported browsers

- **Zen** is intentionally blocked (warning on first run).
- **Midori** is unsupported (upstream decision).
- **Tor / Mullvad**: works, but a first-run notice warns that those projects do not recommend
  installing plugins.

## Flatpak

The fx-autoconfig program files must be copied into the browser's read-only installation, so the
installer cannot patch Flatpak browsers. Follow the upstream fx-autoconfig Flatpak workaround and
install the profile files manually.

## Platform-specific behaviour

- Rounded PiP (`natsumi.pip.rounded`) is Windows-only.
- Translucency/Mica options only apply on macOS and Windows; some desktop environments need a
  compositor (or an external tool such as DWMBlurGlass/MicaForEveryone on Windows).
- The URL bar blur requires `layout.css.backdrop-filter.enabled` and
  `layout.css.backdrop-filter.force-enabled`, plus hardware acceleration.
- Some settings (window material, floating panels) depend on the OS/theme support.

## Settings localization

Chinese translations currently cover the three preferences panes (Customize Noir, About Noir,
Keyboard Shortcuts). The welcome page, in-app notifications and the updater overlay remain in
English. Strings that are not in the dictionary fall back to English by design.
