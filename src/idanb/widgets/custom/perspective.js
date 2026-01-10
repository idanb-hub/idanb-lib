function init() {
    if (window._perspective_hooks_initialized)
        return;

    window._perspective_hooks_initialized = true;
    hookPerspectiveDatagrid();
    makePerspectiveShowCustomToolbar();
}

const tableStyleSheet = new CSSStyleSheet();
tableStyleSheet.replaceSync(`
    td {
        user-select: text !important;
    }
`);

function hookPerspectiveDatagrid() {
    // https://github.com/finos/perspective/blob/master/packages/perspective-viewer-datagrid/src/js/custom_elements/datagrid.js
    const Datagrid = customElements.get("perspective-viewer-datagrid");
    const activate = Datagrid.prototype.activate
    Datagrid.prototype.activate = async function(view) {
        const initialized = this._initialized;

        await activate.call(this, view);

        if (!initialized) {
            makeRegularTableRenderHTML(this.regular_table);

            this.shadowRoot.adoptedStyleSheets.push(tableStyleSheet);
        }
    }
}

// Make regular-table (used by the datagrid plugin) render HTML markup.
function makeRegularTableRenderHTML(regularTable) {
    // https://github.com/finos/regular-table/blob/v0.6.8/README.md#addstylelistener-and-getmeta-styling
    regularTable.addStyleListener(() => {
        for (const td of regularTable.querySelectorAll("td")) {
            // Don't convert when there's some HTML already.
            if (td.children.length > 0)
                continue;
            td.innerHTML = td.textContent;
        }
    });
}

// Add custom toolbar into all registered perspective plugins.
function makePerspectiveShowCustomToolbar() {
    for (const plugin of document.createElement("perspective-viewer").getAllPlugins()) {
        // This seemed like the best method to hook. See:
        //   https://github.com/finos/perspective/blob/master/rust/perspective-viewer/src/rust/js/plugin.rs
        // NOTE: Custom element callbacks can't be hooked.
        const restore = plugin.__proto__.restore;
        plugin.__proto__.restore = function(...params) {
            const viewer = this.parentElement;
            if (viewer) {
                addCustomPluginSettings(viewer);
            }
            return restore.call(this, ...params);
        }
    }
}

function getPluginSettings(viewer) {
    // Plugins can add their settings to their parent perspective-viewer's
    // toolbar through its "plugin-settings" slot. Not all do, so we create
    // a new element when the slot isn't filled.

    const existing = viewer.querySelector("[slot='plugin-settings']");
    if (existing)
        return existing;

    const settings = document.createElement("div");
    settings.setAttribute("slot", "plugin-settings");
    viewer.appendChild(settings);
    return settings;
}

function addCustomPluginSettings(viewer) {
    const settings = getPluginSettings(viewer);
    const root = settings.shadowRoot || settings;

    // Not using `.getElementById` because root can be an arbitrary Element.
    if (root.querySelector("#customPluginSettings"))
        return;

    const custom = document.createElement("div");
    custom.id = "customPluginSettings";
    const shadow = custom.attachShadow({ mode: "open" });

    shadow.adoptedStyleSheets.push(customSettingsStyleSheet);
    shadow.innerHTML = `
        <div id="toolbar">
            <span class="hover-target">
                <span id="maximize" class="button">
                    <span></span>
                </span>
            </span>
        </div>
    `;

    const maximize = shadow.getElementById("maximize");
    maximize.addEventListener("click", (e) => {
        // NOTE: Fullscreen breaks popups.
        viewer.classList.toggle("maximized");
        maximize.classList.toggle("revert");
    });

    root.prepend(custom);
}

const customSettingsStyleSheet = new CSSStyleSheet();
customSettingsStyleSheet.replaceSync(`
    /* https://github.com/finos/perspective/blob/master/packages/perspective-viewer-datagrid/src/less/toolbar.less */

    :host {
        position: relative;
        display: block;
    }

    :host #container {
        position: absolute;
        display: flex;
        flex-direction: column;
        justify-content: stretch;
        align-items: stretch;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
    }

    :host #toolbar {
        display: flex;
        align-items: center;
        height: 36px;
    }

    :host #toolbar .hover-target {
        margin: 0;
        display: inline-flex;
        align-items: center;
        height: 48px;
        cursor: pointer;

        &:hover {
            outline: 4px solid var(--icon--color);
            background-color: var(--icon--color);
        }
    }

    .button:before {
        width: 21px;
        height: 21px;
        content: "";
        -webkit-mask-size: cover;
        mask-size: cover;
        background-color: var(--icon--color);
    }

    .button.editable:before,
    .button.lock-scroll:before {
        color: inherit;
    }

    .button {
        display: inline-flex;
        justify-content: center;
        align-items: center;
        user-select: none;
        padding: 0 5px;
        border: 1px solid transparent;
        border-radius: 3px;
        border: 1px solid transparent;
        box-sizing: border-box;
        display: inline-flex;
        font-size: var(--label--font-size, 0.75em);
        height: 22px;
        user-select: none;
        white-space: nowrap;
        width: 37px;
    }

    .button > span {
        display: none;
        margin: 0;
        padding: 0;
    }

    .hover-target:hover .button {
        position: relative;
        background-color: var(--icon--color);
        color: var(--plugin--background);
        opacity: 1;
        display: flex;
        align-items: center;
        cursor: pointer;
    }

    .hover-target:hover .button:before {
        background-color: var(--plugin--background);
    }

    .hover-target:hover .button > span {
        display: block;
        position: absolute;
        top: calc(100% + 3px);
        left: 50%;
        translate: -50%;
        margin: 0;
        padding: 5px;
        height: auto;
        white-space: pre-wrap;
        line-height: 1;
        font-size: 9px;
        background-color: var(--icon--color);
        width: 35px;
        text-align: center;
        border-radius: 0 0 3px 3px;
    }

    #maximize:before {
        /* https://fontawesome.com/icons/expand?f=classic&s=solid */
        mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA0NDggNTEyIj48IS0tIUZvbnQgQXdlc29tZSBGcmVlIDYuNy4yIGJ5IEBmb250YXdlc29tZSAtIGh0dHBzOi8vZm9udGF3ZXNvbWUuY29tIExpY2Vuc2UgLSBodHRwczovL2ZvbnRhd2Vzb21lLmNvbS9saWNlbnNlL2ZyZWUgQ29weXJpZ2h0IDIwMjUgRm9udGljb25zLCBJbmMuLS0+PHBhdGggZD0iTTMyIDMyQzE0LjMgMzIgMCA0Ni4zIDAgNjRsMCA5NmMwIDE3LjcgMTQuMyAzMiAzMiAzMnMzMi0xNC4zIDMyLTMybDAtNjQgNjQgMGMxNy43IDAgMzItMTQuMyAzMi0zMnMtMTQuMy0zMi0zMi0zMkwzMiAzMnpNNjQgMzUyYzAtMTcuNy0xNC4zLTMyLTMyLTMycy0zMiAxNC4zLTMyIDMybDAgOTZjMCAxNy43IDE0LjMgMzIgMzIgMzJsOTYgMGMxNy43IDAgMzItMTQuMyAzMi0zMnMtMTQuMy0zMi0zMi0zMmwtNjQgMCAwLTY0ek0zMjAgMzJjLTE3LjcgMC0zMiAxNC4zLTMyIDMyczE0LjMgMzIgMzIgMzJsNjQgMCAwIDY0YzAgMTcuNyAxNC4zIDMyIDMyIDMyczMyLTE0LjMgMzItMzJsMC05NmMwLTE3LjctMTQuMy0zMi0zMi0zMmwtOTYgMHpNNDQ4IDM1MmMwLTE3LjctMTQuMy0zMi0zMi0zMnMtMzIgMTQuMy0zMiAzMmwwIDY0LTY0IDBjLTE3LjcgMC0zMiAxNC4zLTMyIDMyczE0LjMgMzIgMzIgMzJsOTYgMGMxNy43IDAgMzItMTQuMyAzMi0zMmwwLTk2eiIvPjwvc3ZnPg==");
        mask-position: center;
        mask-size: 50%;
        mask-repeat: no-repeat;
    }

    #maximize.revert:before {
        /* https://fontawesome.com/icons/compress?f=classic&s=solid */
        mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA0NDggNTEyIj48IS0tIUZvbnQgQXdlc29tZSBGcmVlIDYuNy4yIGJ5IEBmb250YXdlc29tZSAtIGh0dHBzOi8vZm9udGF3ZXNvbWUuY29tIExpY2Vuc2UgLSBodHRwczovL2ZvbnRhd2Vzb21lLmNvbS9saWNlbnNlL2ZyZWUgQ29weXJpZ2h0IDIwMjUgRm9udGljb25zLCBJbmMuLS0+PHBhdGggZD0iTTE2MCA2NGMwLTE3LjctMTQuMy0zMi0zMi0zMnMtMzIgMTQuMy0zMiAzMmwwIDY0LTY0IDBjLTE3LjcgMC0zMiAxNC4zLTMyIDMyczE0LjMgMzIgMzIgMzJsOTYgMGMxNy43IDAgMzItMTQuMyAzMi0zMmwwLTk2ek0zMiAzMjBjLTE3LjcgMC0zMiAxNC4zLTMyIDMyczE0LjMgMzIgMzIgMzJsNjQgMCAwIDY0YzAgMTcuNyAxNC4zIDMyIDMyIDMyczMyLTE0LjMgMzItMzJsMC05NmMwLTE3LjctMTQuMy0zMi0zMi0zMmwtOTYgMHpNMzUyIDY0YzAtMTcuNy0xNC4zLTMyLTMyLTMycy0zMiAxNC4zLTMyIDMybDAgOTZjMCAxNy43IDE0LjMgMzIgMzIgMzJsOTYgMGMxNy43IDAgMzItMTQuMyAzMi0zMnMtMTQuMy0zMi0zMi0zMmwtNjQgMCAwLTY0ek0zMjAgMzIwYy0xNy43IDAtMzIgMTQuMy0zMiAzMmwwIDk2YzAgMTcuNyAxNC4zIDMyIDMyIDMyczMyLTE0LjMgMzItMzJsMC02NCA2NCAwYzE3LjcgMCAzMi0xNC4zIDMyLTMycy0xNC4zLTMyLTMyLTMybC05NiAweiIvPjwvc3ZnPgo=");
    }

    #maximize span:before {
        content: "Expand";
    }

    #maximize.revert span:before {
        content: "Collapse";
        font-size: 0.85em;
    }
`)

init()
