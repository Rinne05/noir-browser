/*

Noir Browser - preferences translations.

Copyright (c) 2026 rinne05
Based on Natsumi Browser, Copyright (c) 2024-present Green (@greeeen-dev).

This file is part of Noir Browser and is licensed under the GNU General Public
License v3.0. See the LICENSE file in the repository for the full text.

*/

/*
Translation helper for the preferences pages.

- Dictionary keys are the English source strings (see i18n-zh.sys.mjs); a
  missing key simply falls back to English, so wrapping can be incremental.
- Language is taken from the browser locale ("zh*" gets Chinese) and can be
  forced with the natsumi.i18n.language pref ("auto" by default).
- localizeDom() walks an already-built subtree and swaps matching text nodes
  and attributes; use t() for strings that are set dynamically.
*/

import * as ucApi from "chrome://userchromejs/content/uc_api.sys.mjs";
import { strings as zhStrings } from "./i18n-zh.sys.mjs";

const languagePref = "natsumi.i18n.language";
const localizedAttributes = ["tooltiptext", "title", "placeholder", "aria-label", "label", "value"];

let cachedLocale = null;

export function getLocale() {
    if (cachedLocale !== null) {
        return cachedLocale;
    }

    let requested = "auto";
    try {
        if (ucApi.Prefs.get(languagePref).exists()) {
            requested = ucApi.Prefs.get(languagePref).value;
        }
    } catch (e) {
        // Pref unavailable; fall through to the browser locale.
    }

    if (requested && requested !== "auto") {
        cachedLocale = requested;
        return cachedLocale;
    }

    try {
        cachedLocale = Services.locale.appLocaleAsBCP47;
    } catch (e) {
        cachedLocale = "en-US";
    }
    return cachedLocale;
}

export function isChinese() {
    return getLocale().toLowerCase().startsWith("zh");
}

export function t(text) {
    if (text === null || text === undefined) {
        return text;
    }
    if (!isChinese()) {
        return text;
    }
    if (Object.prototype.hasOwnProperty.call(zhStrings, text)) {
        return zhStrings[text];
    }
    return text;
}

export function localizeDom(root) {
    if (!root || !isChinese()) {
        return;
    }

    let document = root.ownerDocument ?? root;
    let walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let textNodes = [];
    while (walker.nextNode()) {
        textNodes.push(walker.currentNode);
    }

    for (let node of textNodes) {
        let raw = node.nodeValue;
        if (!raw) {
            continue;
        }
        let trimmed = raw.trim();
        if (!trimmed) {
            continue;
        }
        let key = trimmed;
        if (!Object.prototype.hasOwnProperty.call(zhStrings, key)) {
            // Source template text is often wrapped across lines; compare it
            // with collapsed whitespace so those entries still match.
            let collapsed = trimmed.split(/\s+/).join(" ");
            if (collapsed === trimmed || !Object.prototype.hasOwnProperty.call(zhStrings, collapsed)) {
                continue;
            }
            key = collapsed;
        }
        node.nodeValue = raw.replace(trimmed, zhStrings[key]);
    }

    if (root.querySelectorAll) {
        for (let element of root.querySelectorAll("*")) {
            for (let attribute of localizedAttributes) {
                if (!element.hasAttribute(attribute)) {
                    continue;
                }
                let value = element.getAttribute(attribute);
                if (value && Object.prototype.hasOwnProperty.call(zhStrings, value)) {
                    element.setAttribute(attribute, zhStrings[value]);
                }
            }
        }
    }
}
