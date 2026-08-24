/** @import { AnyWidget } from "@anywidget/types" */
/** @import { HTMLPerspectiveViewerElement, HTMLPerspectiveViewerPluginElement } from "@finos/perspective-viewer" */
/** @import { RegularTableElement } from "regular-table" */
/** @import * as perspective_viewer from "@finos/perspective-viewer/dist/wasm/perspective-viewer.d.ts" */

/**
 * @typedef {import("@finos/perspective-viewer-datagrid").HTMLPerspectiveViewerDatagridPluginElement & { regular_table: RegularTableElement } } HTMLPerspectiveViewerDatagridPluginElement
 */

/**
 * @typedef Traits
 * @property {string} table_name
 * @property {Record<string, string>} config
 * @property {Record<string, string>} styles
 * @property {{[colname: string]: string}} templates
 */

/**
 * @returns {Promise<perspective_viewer>}
 */
async function get_psp_wasm_module() {
  await customElements.whenDefined("perspective-viewer");
  const elem = customElements.get("perspective-viewer");
  // @ts-expect-error: `__wasm_module` is not declared anywhere.
  // eslint-disable-next-line @typescript-eslint/no-unsafe-return
  return elem.__wasm_module__;
}

/**
 * Create and return `<perspective-viewer>` inside parent element.
 * @param {HTMLElement} parent
 * @returns {HTMLPerspectiveViewerElement}
 */
function createViewer(parent) {
  const viewer = document.createElement("perspective-viewer");
  viewer.style.height = "100%";
  viewer.style.minHeight = "200px";

  parent.style.border = "1px solid black";
  parent.style.resize = "vertical";
  // Small initial height, user can resize.
  parent.style.height = "200px";
  parent.replaceChildren(viewer);

  return viewer;
}

/**
 * Apply custom CSS styles to viewer's plugins.
 * @param {HTMLPerspectiveViewerElement} viewer
 * @param {Traits["styles"]} styles
 */
function applyStyles(viewer, styles) {
  for (const [name, style] of Object.entries(styles)) {
    /** @type {HTMLPerspectiveViewerPluginElement | null} */
    let plugin = null;

    try {
      plugin = viewer.getPlugin(name);
    } catch {} // eslint-disable-line no-empty

    if (plugin == null) {
      console.warn("Cannot apply custom style for '%s' plugin.");
      continue;
    }

    const sheet = new CSSStyleSheet();
    if (plugin.shadowRoot != null) {
      sheet.replaceSync(style);
      plugin.shadowRoot.adoptedStyleSheets.push(sheet);
    } else {
      // Add sheet globally, but scope its rules to the `plugin` element.
      sheet.replaceSync(`@scope (${plugin.tagName}) { ${style} }`);
      document.adoptedStyleSheets.push(sheet);
    }
  }
}

/**
 * Allow selecting text inside datagrid table.
 * @param {HTMLPerspectiveViewerDatagridPluginElement} datagrid
 */
function makeTableDataSelectable(datagrid) {
  const sheet = new CSSStyleSheet();
  sheet.replaceSync(`
        td {
            user-select: text !important;
        }
    `);
  datagrid.shadowRoot?.adoptedStyleSheets.push(sheet);

  // Select entire cell contents on double click.
  datagrid.regular_table.addEventListener("mousedown", (e) => {
    if (e.detail !== 2) {
      // Not double click.
      return;
    }

    if (!(e.target instanceof Node)) {
      return;
    }

    const selection = window.getSelection();
    if (selection === null) {
      return;
    }

    const range = document.createRange();
    range.selectNodeContents(e.target);
    selection.removeAllRanges();
    selection.addRange(range);

    e.preventDefault();
  });
}

/**
 * Apply data rendering templates to `<regular-table>`.
 * @param {RegularTableElement} table
 * @param {Traits["templates"]} templates
 */
function applyTemplates(table, templates) {
  const renderers = Object.fromEntries(
    // prettier-ignore
    Object.entries(templates).map(([key, value]) => [
      key,
      /** @type {((value: unknown) => string) | undefined} */
      // eslint-disable-next-line @typescript-eslint/no-implied-eval
      (new Function("$", `return \`${value}\``)),
    ]),
  );

  table.addStyleListener(() => {
    for (const td of table.querySelectorAll("td")) {
      const meta = table.getMeta(td);
      if (meta?.type !== "body") {
        continue;
      }

      const [column] = meta.column_header;
      if (typeof column !== "string") {
        continue;
      }

      // Can be target of attribute selectors in CSS.
      td.dataset.column = column;

      const render = renderers[column];
      if (render !== undefined) {
        td.innerHTML = render(meta.value);
        td.title = td.innerText;
      } else {
        td.title = meta.value?.toString() ?? "";
      }
    }
  });
}

/** @type { AnyWidget<Traits> } */
export default {
  async render({ model, el }) {
    const viewer = createViewer(el);

    applyStyles(viewer, model.get("styles"));

    /** @type {HTMLPerspectiveViewerDatagridPluginElement} */
    const datagrid = viewer.getPlugin("datagrid");
    makeTableDataSelectable(datagrid);
    applyTemplates(datagrid.regular_table, model.get("templates"));

    const { Client } = await get_psp_wasm_module();
    const client = new Client(
      /** @param {Uint8Array} msg */
      // eslint-disable-next-line @typescript-eslint/require-await
      async (msg) => {
        const buffer = msg.slice().buffer;
        model.send({ type: "binary_msg" }, undefined, [buffer]);
      },
    );

    model.on(
      "msg:custom",
      /**
       * @param {Record<string, unknown>} content
       * @param {DataView[]} buffers
       */
      (content, buffers) => {
        // console.log("custom msg", content, buffers);
        switch (content.type) {
          case "binary_msg": {
            const [msg] = buffers;
            void client.handle_response(msg.buffer);
            break;
          }
          default: {
            console.warn("unknown message", content, buffers);
            break;
          }
        }
      },
    );

    /** @type {string[]} */
    const names = [];
    let loading = false;
    /** @type {perspective_viewer.Table | null} */
    let table = null;

    function pushTableName() {
      names.push(model.get("table_name"));
      void loadTable();
    }

    async function loadTable() {
      if (loading) {
        return;
      }

      loading = true;

      while (names.length > 0) {
        const name = names.pop();

        if (table !== null) {
          try {
            await viewer.eject();
            await table.delete({ lazy: true });
          } catch (e) {
            console.error(e);
          }
          table = null;
        }

        if (name) {
          try {
            table = await client.open_table(name);
            await viewer.load(table);
            await viewer.restore(model.get("config"));
          } catch (e) {
            console.error(e);
          }
        }
      }

      loading = false;
    }

    model.on("change:table_name", pushTableName);
    pushTableName();

    function updateConfig() {
      void viewer.restore(model.get("config"));
    }
    model.on("change:config", updateConfig);

    return async () => {
      model.off("change:table_name", pushTableName);
      model.off("change:config", updateConfig);

      await viewer.delete();
      await table?.delete();
    };
  },
};
