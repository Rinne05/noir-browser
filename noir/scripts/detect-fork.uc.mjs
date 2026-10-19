// ==UserScript==
// @include   main
// @ignorecache
// ==/UserScript==

/*

Natsumi Browser - Welcome to your personal internet.

Copyright (c) 2024-present Green (@greeeen-dev)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*/

import * as ucApi from "chrome://userchromejs/content/uc_api.sys.mjs";

function detectFork() {
    let browserName = AppConstants.MOZ_APP_BASENAME.toLowerCase();
    const altBrowserName = AppConstants.MOZ_APP_DISPLAYNAME_DO_NOT_USE.toLowerCase();

    if (altBrowserName === "tor browser") {
        browserName = "torbrowser";
    }

    let forkName = "firefox";

    if (browserName === "floorp") {
        forkName = "floorp";
    } else if (browserName === "firedragon") {
        forkName = "floorp";
        ucApi.Prefs.set("natsumi.browser.type-firedragon", true);

        // For FireDragon, disable Firefox custom theme color
        // This is because the default Sweet-Dark theme causes some issues with contrast with Natsumi
        ucApi.Prefs.set("natsumi.theme.force-natsumi-color", true);
    } else if (browserName === "waterfox") {
        forkName = "waterfox";
    } else if (browserName === "librewolf") {
        forkName = "librewolf";
    } else if (browserName === "mullvadbrowser") {
        forkName = "mullvad";
    } else if (browserName === "torbrowser") {
        forkName = "tor";
    } else if (browserName === "glide") {
        forkName = "glide";
    }

    return forkName;
}

let disableAutoFork = false;

if (ucApi.Prefs.get("natsumi.browser.disable-auto-detect").exists()) {
    disableAutoFork = ucApi.Prefs.get("natsumi.browser.disable-auto-detect").value;
}

if (disableAutoFork) {
    console.warn("Automatic fork detection is disabled.");
} else {
    let forkName = detectFork();

    if (forkName) {
        console.log(`Detected browser fork: ${forkName}`);
        ucApi.Prefs.set("natsumi.browser.type", forkName);

        Services.prefs.addObserver("natsumi.browser.type", () => {
            console.warn("Browser fork changed externally, resetting.");
            ucApi.Prefs.set("natsumi.browser.type", forkName);
        })
    } else {
        console.warn("Could not detect browser fork.");
    }
}
