/*

Noir Browser - quick launch bar.

Copyright (c) 2026 rinne05
Based on Natsumi Browser, Copyright (c) 2024-present Green (@greeeen-dev).

This file is part of Noir Browser and is licensed under the GNU General Public
License v3.0. See the LICENSE file in the repository for the full text.

*/

// ==UserScript==
// @include   main
// @loadOrder 13
// @ignorecache
// ==/UserScript==

import * as ucApi from "chrome://userchromejs/content/uc_api.sys.mjs";

const { PlacesUtils } = ChromeUtils.importESModule("resource://gre/modules/PlacesUtils.sys.mjs");
const { PlacesTransactions } = ChromeUtils.importESModule("resource://gre/modules/PlacesTransactions.sys.mjs");

const folderPref = "natsumi.quicklaunch.folder";
const disabledPref = "natsumi.quicklaunch.disabled";
const dndType = "application/x-natsumi-quicklaunch-item";

const bookmarkEvents = [
    "bookmark-added",
    "bookmark-removed",
    "bookmark-moved",
    "bookmark-title-changed",
    "bookmark-url-changed",
];
const faviconEvents = ["favicon-changed"];

class NatsumiQuickLaunch {
    constructor() {
        this.node = null;
        this.renderId = 0;
        this.renderTimer = 0;
        this.renderPending = false;
        this.items = [];
        this.itemUris = new Set();
        this.activeGuid = "";
        this.folderGuid = "";
        this.folderChildrenGuids = [];
        this.dragState = null;
        this.suppressNotifications = false;
        this.contextMenu = null;
        this.contextBookmark = null;
    }

    init() {
        let tabBrowserNode = document.getElementById("tabbrowser-tabs");
        if (!tabBrowserNode) {
            return;
        }

        let container = document.createElement("div");
        container.id = "natsumi-quicklaunch";
        container.hidden = true;

        // Place it at the very top of the tab strip, above the pinned tabs.
        // insertBefore is required here; appending directly breaks the tab strip.
        let reference = document.getElementById("pinned-tabs-container")
            ?? document.getElementById("vertical-pinned-tabs-splitter")
            ?? document.getElementById("natsumi-tabs-clearer")
            ?? document.getElementById("tabbrowser-arrowscrollbox");
        if (reference) {
            tabBrowserNode.insertBefore(container, reference);
        } else {
            tabBrowserNode.appendChild(container);
        }

        this.node = container;
        this.render();

        // Dragging an item reorders the grid and writes the new order back to
        // the source folder.
        container.addEventListener("dragstart", (event) => this.onDragStart(event));
        container.addEventListener("dragover", (event) => this.onDragOver(event));
        container.addEventListener("drop", (event) => this.onDrop(event));
        container.addEventListener("dragend", (event) => this.onDragEnd(event));

        // Keyboard: one tab stop for the whole grid, arrow keys move within it,
        // like the tab strip.
        container.addEventListener("focusin", (event) => this.onFocusIn(event));
        container.addEventListener("keydown", (event) => this.onKeyDown(event));

        // Right-clicking a tile must show bookmark actions, not the sidebar
        // menu inherited from #sidebar-container.
        container.addEventListener("contextmenu", (event) => this.onContextMenu(event));
        this.initContextMenu();

        // Keep the bar in sync with bookmark and favicon changes while the
        // window stays focused.
        this.bookmarkListener = (events) => this.onBookmarkEvents(events);
        this.faviconListener = (events) => this.onFaviconEvents(events);
        PlacesUtils.observers.addListener(bookmarkEvents, this.bookmarkListener);
        PlacesUtils.observers.addListener(faviconEvents, this.faviconListener);
        window.addEventListener("unload", () => {
            PlacesUtils.observers.removeListener(bookmarkEvents, this.bookmarkListener);
            PlacesUtils.observers.removeListener(faviconEvents, this.faviconListener);
        }, { once: true });

        Services.prefs.addObserver(folderPref, () => this.render());
        Services.prefs.addObserver(disabledPref, () => this.render());
    }

    async render() {
        if (!this.node) {
            return;
        }

        // Never rebuild the grid in the middle of a drag; the drop or cancel
        // flushes the pending render afterwards.
        if (this.dragState) {
            this.renderPending = true;
            return;
        }

        let renderId = ++this.renderId;
        this.renderPending = false;

        let disabled = false;
        if (ucApi.Prefs.get(disabledPref).exists()) {
            disabled = ucApi.Prefs.get(disabledPref).value;
        }

        let folderGuid = "";
        if (ucApi.Prefs.get(folderPref).exists()) {
            folderGuid = ucApi.Prefs.get(folderPref).value;
        }

        this.finishDrag();

        if (disabled || !folderGuid) {
            this.items = [];
            this.itemUris = new Set();
            this.activeGuid = "";
            this.folderGuid = "";
            this.folderChildrenGuids = [];
            this.node.replaceChildren();
            this.node.hidden = true;
            return;
        }

        let children = [];
        try {
            let tree = await PlacesUtils.promiseBookmarksTree(folderGuid);
            children = tree?.children ?? [];
        } catch(e) {
            console.error("Failed to read quick launch folder:", e);
        }

        // A newer render started while this one was reading the bookmarks
        if (renderId !== this.renderId) {
            return;
        }

        let hadFocus = this.node.contains(document.activeElement);

        this.folderGuid = folderGuid;
        this.folderChildrenGuids = children.map(child => child.guid);
        this.items = children
            .filter(child => child.uri)
            .map(bookmark => ({
                guid: bookmark.guid,
                uri: bookmark.uri,
                element: this.createItem(bookmark),
            }));
        this.itemUris = new Set(this.items.map(item => item.uri));

        let active = this.items.find(item => item.guid === this.activeGuid)
            ?? this.items[0];
        this.activeGuid = active?.guid ?? "";
        for (let item of this.items) {
            item.element.tabIndex = item === active ? 0 : -1;
        }

        this.node.replaceChildren(...this.items.map(item => item.element));
        this.node.hidden = this.items.length === 0;

        if (hadFocus && active) {
            active.element.focus();
        }
    }

    createItem(bookmark) {
        let item = document.createElement("button");
        item.type = "button";
        item.className = "natsumi-quicklaunch-item";
        item.draggable = true;

        let title = bookmark.title || bookmark.uri;
        item.title = title;
        item.setAttribute("aria-label", title);

        item.addEventListener("click", () => {
            openWebLinkIn(bookmark.uri, "tab");
        });

        item.addEventListener("auxclick", (event) => {
            if (event.button === 1) {
                event.preventDefault();
                openWebLinkIn(bookmark.uri, "tab", {inBackground: true});
            }
        });

        let icon = document.createElement("img");
        icon.alt = "";
        icon.addEventListener("error", () => {
            icon.remove();
            item.classList.add("natsumi-quicklaunch-item-noicon");
        });
        item.appendChild(icon);
        this.loadIcon(icon, bookmark.uri);

        return item;
    }

    // Ask the favicon service instead of using `page-icon:` directly: the
    // service waits for the favicon database, while an early `page-icon:`
    // request can be served with the default icon on startup.
    async loadIcon(icon, uri) {
        try {
            let favicon = await PlacesUtils.favicons.getFaviconForPage(
                Services.io.newURI(uri)
            );
            if (favicon?.dataURI?.spec) {
                if (icon.isConnected) {
                    icon.src = favicon.dataURI.spec;
                }
                return;
            }
        } catch(e) {
            // No favicon stored for this page; fall back to the default.
        }

        if (icon.isConnected) {
            icon.src = `page-icon:${uri}`;
        }
    }

    /* Context menu */

    initContextMenu() {
        let popup = document.createXULElement("menupopup");
        popup.id = "natsumi-quicklaunch-context";

        let addItem = (l10nId, args, handler, isDefault = false) => {
            let item = document.createXULElement("menuitem");
            item.setAttribute("data-l10n-id", l10nId);
            if (args) {
                item.setAttribute("data-l10n-args", JSON.stringify(args));
            }
            if (isDefault) {
                item.setAttribute("default", "true");
            }
            item.addEventListener("command", () => {
                popup.hidePopup();
                handler();
            });
            popup.appendChild(item);
            return item;
        };

        addItem("places-open-in-tab", null,
            () => this.openContextBookmark("tab"), true);
        addItem("places-open-in-window", null,
            () => this.openContextBookmark("window"));
        addItem("places-open-in-private-window", null,
            () => this.openContextBookmark("private-window"));
        popup.appendChild(document.createXULElement("menuseparator"));
        addItem("text-action-copy", null,
            () => this.copyContextLink());
        popup.appendChild(document.createXULElement("menuseparator"));
        addItem("places-edit-bookmark", null,
            () => this.editContextBookmark());
        addItem("places-delete-bookmark", null,
            () => this.removeContextBookmark());

        document.documentElement.appendChild(popup);
        document.l10n?.translateElements([popup]).catch(() => {});
        this.contextMenu = popup;
    }

    onContextMenu(event) {
        // The sidebar background is a context-menu region; the launcher is
        // not, so the inherited sidebar menu must never appear here.
        event.preventDefault();
        event.stopPropagation();

        let element = event.target?.closest?.(".natsumi-quicklaunch-item");
        if (!element) {
            return;
        }

        let index = this.items.findIndex(item => item.element === element);
        if (index < 0) {
            return;
        }

        this.contextBookmark = this.items[index];
        if (this.contextMenu.state === "open") {
            this.contextMenu.hidePopup();
        }

        // Keyboard-triggered context menus may not carry screen coordinates.
        let rect = element.getBoundingClientRect();
        let x = event.screenX || Math.round(window.screenX + rect.left);
        let y = event.screenY || Math.round(window.screenY + rect.bottom);
        this.contextMenu.openPopupAtScreen(x, y, true);
    }

    openContextBookmark(where) {
        if (!this.contextBookmark) {
            return;
        }
        openWebLinkIn(this.contextBookmark.uri, where);
    }

    copyContextLink() {
        if (!this.contextBookmark) {
            return;
        }
        let clipboard = Cc["@mozilla.org/widget/clipboardhelper;1"]
            .getService(Ci.nsIClipboardHelper);
        clipboard.copyString(this.contextBookmark.uri);
    }

    // The edit dialog wants an nsINavHistoryResultNode, so query the parent
    // folder and keep the container open until the dialog is closed.
    async getBookmarkResult(guid) {
        let bookmark = await PlacesUtils.bookmarks.fetch(guid);
        if (!bookmark) {
            return null;
        }

        let query = {};
        let options = {};
        PlacesUtils.history.queryStringToQuery(
            `place:parent=${bookmark.parentGuid}`, query, options
        );
        let result = PlacesUtils.history.executeQuery(query.value, options.value);
        let root = result.root;
        root.containerOpen = true;

        for (let i = 0; i < root.childCount; i++) {
            let node = root.getChild(i);
            if (node.bookmarkGuid === guid) {
                return { node, root };
            }
        }

        root.containerOpen = false;
        return null;
    }

    async editContextBookmark() {
        let bookmark = this.contextBookmark;
        if (!bookmark) {
            return;
        }

        let found = null;
        try {
            found = await this.getBookmarkResult(bookmark.guid);
            if (!found) {
                return;
            }
            await window.PlacesUIUtils.showBookmarkDialog(
                { action: "edit", type: "bookmark", node: found.node },
                window
            );
        } catch(e) {
            console.error("Failed to edit quick launch bookmark:", e);
        } finally {
            if (found?.root) {
                found.root.containerOpen = false;
            }
        }
    }

    async removeContextBookmark() {
        let bookmark = this.contextBookmark;
        if (!bookmark) {
            return;
        }

        try {
            await PlacesTransactions.Remove({ guids: [bookmark.guid] }).transact();
        } catch(e) {
            console.error("Failed to remove quick launch bookmark:", e);
        }
    }

    /* Live updates and keyboard navigation */

    scheduleRender() {
        if (this.dragState) {
            this.renderPending = true;
            return;
        }

        if (this.renderTimer) {
            window.clearTimeout(this.renderTimer);
        }

        this.renderTimer = window.setTimeout(() => {
            this.renderTimer = 0;
            if (this.dragState) {
                this.renderPending = true;
                return;
            }
            this.render();
        }, 250);
    }

    onBookmarkEvents(events) {
        if (this.suppressNotifications || !this.folderGuid) {
            return;
        }

        let folderGuid = this.folderGuid;
        let relevant = events.some(event =>
            event.parentGuid === folderGuid || event.oldParentGuid === folderGuid
        );
        if (relevant) {
            this.scheduleRender();
        }
    }

    onFaviconEvents(events) {
        if (!this.itemUris.size) {
            return;
        }

        if (events.some(event => this.itemUris.has(event.url))) {
            this.scheduleRender();
        }
    }

    onFocusIn(event) {
        let element = event.target?.closest?.(".natsumi-quicklaunch-item");
        if (!element) {
            return;
        }

        let index = this.items.findIndex(item => item.element === element);
        if (index < 0) {
            return;
        }

        this.activeGuid = this.items[index].guid;
        this.updateTabStops(index);
    }

    updateTabStops(activeIndex) {
        for (let i = 0; i < this.items.length; i++) {
            this.items[i].element.tabIndex = i === activeIndex ? 0 : -1;
        }
    }

    onKeyDown(event) {
        let element = event.target?.closest?.(".natsumi-quicklaunch-item");
        if (!element) {
            return;
        }

        let index = this.items.findIndex(item => item.element === element);
        if (index < 0) {
            return;
        }

        let next = index;
        switch (event.key) {
            case "ArrowLeft":
                next = Math.max(0, index - 1);
                break;
            case "ArrowRight":
                next = Math.min(this.items.length - 1, index + 1);
                break;
            case "ArrowUp":
                next = this.findVerticalNeighbor(index, -1);
                break;
            case "ArrowDown":
                next = this.findVerticalNeighbor(index, 1);
                break;
            case "Home":
                next = 0;
                break;
            case "End":
                next = this.items.length - 1;
                break;
            default:
                return;
        }

        event.preventDefault();

        if (next < 0 || next === index) {
            return;
        }

        this.activeGuid = this.items[next].guid;
        this.updateTabStops(next);
        this.items[next].element.focus();
    }

    // Nearest tile in the row above (-1) or below (1).
    findVerticalNeighbor(index, direction) {
        let rects = this.items.map(item => item.element.getBoundingClientRect());
        let current = rects[index];
        if (!current) {
            return index;
        }

        let center = current.left + (current.width / 2);
        let best = index;
        let bestScore = Infinity;

        for (let i = 0; i < rects.length; i++) {
            if (i === index) {
                continue;
            }

            let rect = rects[i];
            if (direction < 0 ? rect.top >= current.top : rect.top <= current.top) {
                continue;
            }

            let dy = Math.abs(rect.top - current.top);
            let dx = Math.abs(rect.left + (rect.width / 2) - center);
            // The vertical distance dominates so the nearest row always wins;
            // within that row the closest column is chosen.
            let score = (dy * 1000) + dx;
            if (score < bestScore) {
                bestScore = score;
                best = i;
            }
        }

        return best;
    }

    /* Drag to reorder */

    onDragStart(event) {
        let element = event.target?.closest?.(".natsumi-quicklaunch-item");
        if (!element) {
            return;
        }

        let index = this.items.findIndex(item => item.element === element);
        if (index < 0) {
            return;
        }

        // Our events bubble into the tab strip, whose drag handlers assume
        // tab data; keep them to ourselves.
        event.stopPropagation();

        let rect = element.getBoundingClientRect();
        let nodeRect = this.node.getBoundingClientRect();
        let stripRect = document.getElementById("tabbrowser-tabs").getBoundingClientRect();
        let dataTransfer = event.dataTransfer;

        // A custom type keeps other drop targets (tab strip, URL bar, ...)
        // from treating the drag as a link.
        dataTransfer.effectAllowed = "move";
        dataTransfer.setData(dndType, this.items[index].guid);

        // Hide the platform drag feedback; the tile copy below is what follows
        // the pointer.
        let blank = document.createElement("div");
        blank.className = "natsumi-quicklaunch-item-blank";
        this.node.appendChild(blank);
        try {
            dataTransfer.setDragImage(blank, 0, 0);
        } catch(e) {
            // Dragging still works without a custom drag image.
        }

        // Absolute inside the grid container: the sidebar adds a transform,
        // so `fixed` would be relative to the sidebar, not the viewport.
        let follower = element.cloneNode(true);
        follower.classList.add("natsumi-quicklaunch-item-follower");
        follower.tabIndex = -1;
        follower.draggable = false;
        follower.setAttribute("aria-hidden", "true");
        follower.style.left = (rect.left - nodeRect.left) + "px";
        follower.style.top = (rect.top - nodeRect.top) + "px";
        follower.style.width = rect.width + "px";
        follower.style.height = rect.height + "px";
        follower.style.margin = "0";
        this.node.appendChild(follower);

        // A single-column grid (collapsed launcher) is sorted by the vertical
        // position; multi-column grids by the horizontal position in a row.
        let rects = this.items.map(item => item.element.getBoundingClientRect());
        let firstTop = rects[0]?.top ?? 0;
        let singleColumn =
            rects.filter(rect => Math.abs(rect.top - firstTop) < 1).length === 1;

        this.dragState = {
            index,
            element,
            follower,
            blank,
            nodeRect,
            itemWidth: rect.width,
            startLeft: rect.left - nodeRect.left,
            startTop: rect.top - nodeRect.top,
            startX: event.clientX,
            startY: event.clientY,
            // A dragged tab can move over the whole tab strip, not just over
            // its own section, so clamp vertically to the strip.
            minTop: stripRect.top - nodeRect.top,
            maxTop: stripRect.bottom - nodeRect.top - rect.height,
            slot: index + 1,
            // Layout positions never change while dragging, so measure once:
            // the shifted tiles then can not feed back into the calculation.
            rects,
            singleColumn,
        };

        this.node.classList.add("natsumi-quicklaunch-dragging");
        element.classList.add("natsumi-quicklaunch-item-dragging");
    }

    onDragOver(event) {
        if (!this.dragState) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.dataTransfer.dropEffect = "move";

        this.moveFollower(event.clientX, event.clientY);

        let slot = this.slotAt(event.clientX, event.clientY);
        if (slot !== this.dragState.slot) {
            this.dragState.slot = slot;
            this.applyGap();
        }
    }

    onDrop(event) {
        if (!this.dragState) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        let {follower, nodeRect, rects} = this.dragState;
        let targetRect = rects[this.targetIndex()];

        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            this.finalizeDrag();
            return;
        }

        // Slide the tile into the open slot, like the drop animation of a
        // dragged pinned tab; the order is committed once it arrives.
        let left = parseFloat(follower.style.left) || 0;
        let top = parseFloat(follower.style.top) || 0;
        let dx = targetRect.left - nodeRect.left - left;
        let dy = targetRect.top - nodeRect.top - top;

        this.dragState.settling = true;
        follower.style.transform = `translate(${dx}px, ${dy}px)`;
        this.dragState.settleTimer = window.setTimeout(() => {
            if (this.dragState) {
                this.finalizeDrag();
            }
        }, 220);
    }

    onDragEnd(event) {
        event.stopPropagation();

        // The drop already scheduled the commit and its animation.
        if (this.dragState?.settling) {
            return;
        }

        this.finishDrag();
        this.flushPendingRender();
    }

    finalizeDrag() {
        if (!this.dragState) {
            return;
        }

        let target = this.targetIndex();
        let items = [...this.items];
        let [moved] = items.splice(this.dragState.index, 1);
        items.splice(target, 0, moved);

        this.finishDrag();
        this.items = items;
        this.node.replaceChildren(...items.map(item => item.element));

        this.persistOrder().catch(error => {
            console.error("Failed to save quick launch order:", error);
            this.render();
        }).finally(() => {
            this.flushPendingRender();
        });
    }

    // Keep the tile under the pointer, clamped inside the tab strip, the same
    // way a dragged tab is clamped.
    moveFollower(x, y) {
        let {nodeRect, itemWidth, startLeft, startTop, startX, startY,
             minTop, maxTop, follower} = this.dragState;

        let left = Math.min(
            Math.max(startLeft + (x - startX), 0),
            nodeRect.width - itemWidth
        );
        let top = Math.min(
            Math.max(startTop + (y - startY), minTop),
            maxTop
        );

        follower.style.left = left + "px";
        follower.style.top = top + "px";
    }

    // Insertion slot (0 = before the first item) for a pointer position.
    slotAt(x, y) {
        let {rects, singleColumn} = this.dragState;

        for (let i = 0; i < rects.length; i++) {
            let rect = rects[i];

            // Above this row: insert before its first tile.
            if (y < rect.top) {
                return i;
            }
            if (y <= rect.bottom) {
                if (singleColumn) {
                    return y < rect.top + (rect.height / 2) ? i : i + 1;
                }
                // In a row: keep walking while the pointer is past the middle
                // of the tile, otherwise insert before it.
                if (x < rect.left + (rect.width / 2)) {
                    return i;
                }
                continue;
            }
        }

        return rects.length;
    }

    // The slot above counts the dragged tile itself, so shift it by one when
    // it moves forward.
    targetIndex() {
        let {index, slot} = this.dragState;
        return slot > index ? slot - 1 : slot;
    }

    // Slide the other tiles one cell over so the drop slot stays open.
    applyGap() {
        let {index, rects} = this.dragState;
        let order = this.items.map((_, itemIndex) => itemIndex);
        order.splice(index, 1);
        order.splice(this.targetIndex(), 0, index);

        for (let cell = 0; cell < order.length; cell++) {
            let origin = order[cell];
            if (origin === index) {
                continue;
            }

            let from = rects[origin];
            let to = rects[cell];
            this.items[origin].element.style.transform =
                `translate(${to.left - from.left}px, ${to.top - from.top}px)`;
        }
    }

    clearGap() {
        for (let item of this.items) {
            item.element.style.transform = "";
        }
    }

    finishDrag() {
        if (this.dragState) {
            let {element, follower, blank, settleTimer} = this.dragState;

            if (settleTimer) {
                window.clearTimeout(settleTimer);
            }

            element.classList.remove("natsumi-quicklaunch-item-dragging");
            follower.remove();
            blank.remove();
            this.dragState = null;
        }

        this.node?.classList.remove("natsumi-quicklaunch-dragging");
        this.clearGap();
    }

    // A bookmark/favicon change that arrived while dragging is applied after
    // the drop (or cancel) has settled.
    flushPendingRender() {
        if (!this.renderPending) {
            return;
        }

        this.renderPending = false;
        this.render();
    }

    // Keep the order of the source folder in sync, leaving any children that
    // are not shown (subfolders) where they are.
    async persistOrder() {
        if (!this.folderGuid || !this.folderChildrenGuids.length) {
            return;
        }

        let visible = new Set(this.items.map(item => item.guid));
        let orderedItems = this.items.map(item => item.guid);
        let orderedChildren = this.folderChildrenGuids.map(guid =>
            visible.has(guid) ? orderedItems.shift() ?? guid : guid
        );

        // Our own reorder fires bookmark-moved; do not re-render for it.
        this.suppressNotifications = true;
        try {
            await PlacesUtils.bookmarks.reorder(this.folderGuid, orderedChildren);
            this.folderChildrenGuids = orderedChildren;
        } finally {
            window.setTimeout(() => {
                this.suppressNotifications = false;
            }, 300);
        }
    }
}

if (!document.body.natsumiQuickLaunch) {
    document.body.natsumiQuickLaunch = new NatsumiQuickLaunch();
    document.body.natsumiQuickLaunch.init();
}
