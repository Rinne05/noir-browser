# Configuration reference

Noir keeps the upstream `natsumi.*` pref namespace (the internal prefix was deliberately not
renamed — see [`NOTICE`](../NOTICE)). All preferences are optional: when a pref is unset the
documented default applies, which is also why they do not appear in `about:config` until you
create them.

With the full version installed, almost everything is available in **Settings → Customize Noir**.
Otherwise create the prefs manually in `about:config` (use the **+** button and pick the right
type).

## Theming and general

| Pref | Type | Values | Description |
|---|---|---|---|
| `natsumi.theme.type` | string | `default` (default), `gradient`, `gradient-complementary`, `colorful`, `playful`, `lucid`, `frutiger-aero`, `oled`, `lgbtq`, `transgender`, `custom` | Browser theme |
| `natsumi.theme.accent-color` | string | `light-green` (default), `sky-blue`, `turquoise`, `yellow`, `peach-orange`, `warmer-pink`, `beige`, `light-red`, `muted-pink`, `pink`, `lavender-purple`, `system` | Accent color preset |
| `natsumi.theme.force-natsumi-color` | boolean | — | Use Noir's accent color instead of the Firefox theme color |
| `natsumi.theme.use-tab-theme-color` | boolean | — | Use the tab border color as Blade's accent color |
| `natsumi.theme.max-custom-colors` | integer | default `6` | Maximum number of custom theme colors |
| `natsumi.theme.disable-translucency` | boolean | — | Disable the translucency effect |
| `natsumi.theme.use-legacy-translucency` | boolean | — | Legacy translucency (macOS/Windows) |
| `natsumi.theme.gray-out-when-inactive` | boolean | — | Gray out the browser when the window is inactive |
| `natsumi.theme.browser-separation` | integer | default `6` | Margin between browser UI and web content |
| `natsumi.theme.font` | string | `default` or a font family | UI font |
| `natsumi.theme.font-size-offset` | integer | — | Font size offset |
| `natsumi.theme.icons` | string | `default`, `lucide`, `fluent` | Icon pack |
| `natsumi.theme.icons-alt-back-forward` | boolean | — | Alternate back/forward icons |
| `natsumi.theme.classic-preferences` | boolean | — | Disable the redesigned preferences page |
| `natsumi.theme.ignore-css-issues` | boolean | — | Hide the CSS loading warning |
| `natsumi.theme.disable-sdl2` | boolean | — | Disable the Starlight Design 2 material |
| `natsumi.theme.floorp-hide-preferences-warnings` | boolean | — | Hide Floorp Hub warnings **Floorp** |
| `natsumi.theme.disable-patches` | boolean | — | Disable fork version patches |
| `natsumi.theme.patch-undo-closed-tab-button` | boolean | — | Hide Floorp's undo-closed-tab button **Floorp** |

## Layout, Compact Mode and Single Toolbar

| Pref | Type | Values | Description |
|---|---|---|---|
| `natsumi.theme.single-toolbar` | boolean | — | Single Toolbar layout |
| `natsumi.theme.single-toolbar-show-menu-button` | boolean | — | Show the menu button in Single Toolbar |
| `natsumi.theme.single-toolbar-hide-extensions-button` | boolean | — | Hide the extensions button in Single Toolbar |
| `natsumi.theme.show-bookmarks-on-hover` | boolean | — | Show the bookmarks bar on hover in Single Toolbar |
| `natsumi.theme.compact-marginless` | boolean | — | Remove the frame around web content in Compact Mode |
| `natsumi.theme.compact-on-new-window` | boolean | — | Enable Compact Mode for new windows |
| `natsumi.theme.compact-style` | string | `default` (both hidden), `toolbar`, `sidebar` | What Compact Mode hides |
| `natsumi.theme.force-window-controls-to-left` | boolean | — | Put window controls in the sidebar |

## Tabs and sidebar

| Pref | Type | Values | Description |
|---|---|---|---|
| `natsumi.tabs.use-custom-type` | boolean | — | Enable custom tab designs (Blade is used otherwise) |
| `natsumi.tabs.type` | string | `default` (Blade), `origin`, `curve`, `fusion`, `material`, `hexagonal`, `classic`, `bubble`, `clicky`, `neutron` | Tab design |
| `natsumi.tabs.blade-legacy-color` | boolean | — | Legacy Blade highlight color |
| `natsumi.tabs.fusion-highlight` | boolean | — | Photon-like highlight for Fusion tabs |
| `natsumi.tabs.material-alt-design` | boolean | — | Alternative Material design |
| `natsumi.tabs.new-tab-on-top` | boolean | — | Move the new-tab button to the top |
| `natsumi.tabs.replace-new-tab` | boolean | — | Open the URL bar instead of a new tab |
| `natsumi.tabs.workspace-specific-pins` | boolean | — | Workspace-specific pinned tabs **Floorp** |
| `natsumi.sidebar.hide-clear-tabs` | boolean | — | Hide the "clear unpinned tabs" button |
| `natsumi.sidebar.clear-keep-selected` | boolean | — | Keep selected tabs when clearing |
| `natsumi.sidebar.clear-open-newtab` | boolean | — | Open a new tab after clearing |
| `natsumi.sidebar.clear-merge-with-workspaces` | boolean | — | Merge the clear button with the Workspaces indicator **Floorp** |
| `natsumi.sidebar.hide-sidebar-controls` | boolean | — | Hide sidebar controls |
| `natsumi.sidebar.disable-bottom-toolbar` | boolean | — | Disable the bottom toolbar |
| `natsumi.sidebar.disable-clickable-workspace-icons` | boolean | — | Disable clickable workspace icons **Floorp** |
| `natsumi.sidebar.floorp-floating-panel` | boolean | — | Float the Panel Sidebar like Compact Mode **Floorp** |
| `natsumi.sidebar.hide-workspace-indicator` | boolean | — | Hide Noir's Workspaces indicator **Floorp** |
| `natsumi.sidebar.legacy-workspace-indicator` | boolean | — | Use the legacy Workspaces indicator **Floorp** |
| `natsumi.sidebar.workspaces-as-icons` | boolean | — | Show workspaces as an icon strip **Floorp** |

## URL bar and findbar

| Pref | Type | Values | Description |
|---|---|---|---|
| `natsumi.urlbar.disabled` | boolean | — | Disable URL bar tweaks |
| `natsumi.urlbar.do-not-float` | boolean | — | Disable the floating URL bar |
| `natsumi.urlbar.always-expanded` | boolean | — | Disable the compact URL bar when inactive |
| `natsumi.urlbar.single-toolbar-display-actions` | boolean | — | Show action buttons on hover in Single Toolbar |
| `natsumi.urlbar.show-kit` | boolean | — | Show Kit on the trust panel |
| `natsumi.findbar.disabled` | boolean | — | Disable the Noir findbar |
| `natsumi.findbar.disable-not-found-bg` | boolean | — | Disable the red "not found" background |
| `natsumi.findbar.wider-findbar` | boolean | — | Raise the maximum findbar width to 720px |

## Miniplayer and Glimpse

| Pref | Type | Values | Description |
|---|---|---|---|
| `natsumi.miniplayer.disable-artwork` | boolean | — | Hide artwork in the Miniplayer |
| `natsumi.miniplayer.scroll-view` | boolean | — | Make the Miniplayer list scrollable |
| `natsumi.experiments.miniplayer-seekbar` | boolean | — | Experimental Miniplayer seekbar |
| `natsumi.glimpse.enabled` | boolean | — | Enable Glimpse |
| `natsumi.glimpse.multi` | boolean | — | Enable Multi Glimpse (required for chaining) |
| `natsumi.glimpse.key` | string | `alt`, `ctrl`, `meta`, `shift`, `hold` | Activation method |
| `natsumi.glimpse.controls-on-right` | boolean | — | Move Glimpse controls to the right |
| `natsumi.glimpse.alt-border` | boolean | — | Alternate border color for Glimpse tabs |
| `natsumi.glimpse.show-indicator` | boolean | — | Show the Glimpse indicator |

## Picture-in-Picture, PDF viewer and home page

| Pref | Type | Values | Description |
|---|---|---|---|
| `natsumi.pip.disabled` | boolean | — | Disable the Noir PiP design |
| `natsumi.pip.disable-scroll-to-move` | boolean | — | Disable scroll-to-move |
| `natsumi.pip.legacy-style` | boolean | — | Merge PiP controls into one island |
| `natsumi.pip.material` | string | `haze` (default), `tinted-haze` | Material used by PiP controls |
| `natsumi.pip.rounded` | boolean | — | Rounded PiP window **Windows only** |
| `natsumi.pdfjs.disabled` | boolean | — | Disable the Noir PDF viewer |
| `natsumi.pdfjs.compact` | boolean | — | Toolbar autohide in the PDF viewer |
| `natsumi.pdfjs.compact-dynamic` | boolean | — | Disable autohide while the PDF sidebar is open |
| `natsumi.pdfjs.material` | string | `haze` (default), `tinted-haze` | Material used by the PDF viewer |
| `natsumi.home.disabled` | boolean | — | Disable the Noir home page |
| `natsumi.home.custom-background` | boolean | — | Use the configured background on the home page |

## Startup

| Pref | Type | Values | Description |
|---|---|---|---|
| `natsumi.startup.type` | string | `default` (disabled), `simple`, `nostalgic` | Startup animation |
| `natsumi.startup.icon` | string | `default`, `kawaii`, `pride`, `stardust`, `custom` | Icon shown during the startup animation. `default` follows the theme (glass, or pride with the LGBTQ+ theme); `custom` uses the uploaded image |
| `natsumi.startup.custom-icon-id` | string | file ID | Uploaded icon (set through Settings → Customize Noir → Startup) |
| `natsumi.startup.sound` | string | `default` (none), `borealis`, `custom` | Startup sound |
| `natsumi.startup.custom-sound-id` | string | file ID | Uploaded sound (set through Settings) |

The custom icon is stored in the profile under `natsumi-uploads/` (JSON-wrapped data URL).

## Compatibility, updates and language

| Pref | Type | Values | Description |
|---|---|---|---|
| `natsumi.browser.type` | string | `firefox`, `floorp`, `waterfox`, `librewolf`, `tor`, `mullvad`, `firedragon`, `glide` | Browser type used by fork-gated CSS; set automatically by Append |
| `natsumi.browser.disable-auto-detect` | boolean | — | Disable automatic browser detection (restart required) |
| `natsumi.updater.disabled` | boolean | — | Disable the auto-updater |
| `natsumi.updater.branch` | string | `stable` (default), `rc`, `beta`, `alpha` | Update channel |
| `natsumi.updater.keep-old-versions` | boolean | — | Keep `noir-old` after an update |
| `natsumi.i18n.language` | string | `auto` (default), `en`, `zh-CN` | Settings UI language |

## Floorp / Waterfox notes

Floorp integrations (workspaces, split view, panel sidebar, command palette, web apps, gestures)
and Waterfox's status bar are activated automatically through `natsumi.browser.type`. They are
inert on Firefox and do not need to be configured. See
[`KNOWN-ISSUES.md`](KNOWN-ISSUES.md#floorp-only-and-waterfox-only-features) for the list.
