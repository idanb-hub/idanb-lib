/** @import { AnyWidget, Render } from "@anywidget/types" */

/** @type {import("ansi_up")} */
// @ts-expect-error: Can't find types for CDN import.
const { AnsiUp } = await import("https://esm.sh/ansi_up@6");
const ansi_up = new AnsiUp();

/**
 * @typedef Traits
 * @property {number} level
 * @property {Record<string, number>} all_levels
 */

/** @type { Render<Traits> } */
function render({ model, el }) {
  el.classList.add("widget-logs");
  el.innerHTML = `
        <details class="widget-logs__expandable">
            <summary>
                Logs
                <div class="widget-logs__controls">
                    <select class="widget-logs__levels"></select>
                    <button class="widget-logs__clear">clear</button>
                </div>
            </Summary>
            <pre class="widget-logs__logs"></pre>
        </details>
        <pre class="widget-logs__status"></pre>
    `;

  /**
   * @param {string} selector
   * @returns {any}
   */
  function getChild(selector) {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-return
    return el.querySelector(selector);
  }

  /** @type {HTMLElement} */
  const logsElement = getChild(".widget-logs__logs");
  /** @type {HTMLElement} */
  const statusElement = getChild(".widget-logs__status");
  /** @type {HTMLSelectElement} */
  const levelsSelect = getChild("select.widget-logs__levels");
  /** @type {HTMLButtonElement} */
  const clearButton = getChild("button.widget-logs__clear");

  clearButton.addEventListener("click", () => {
    logsElement.replaceChildren();
    log("Output has been cleared.\n");
  });

  /**
   * @param {string} html
   */
  function log(html) {
    statusElement.innerHTML = html;
    const child = document.createElement("span");
    child.innerHTML = html;
    logsElement.appendChild(child);
  }

  model.on(
    "msg:custom",
    /** @param {string} msg */
    (msg) => {
      log(ansi_up.ansi_to_html(msg));
    },
  );

  function updateAllLevels() {
    const allLevels = model.get("all_levels");
    const options = Object.entries(allLevels).map(([name, level]) => {
      const option = document.createElement("option");
      option.textContent = name;
      option.value = level.toString();
      return option;
    });
    levelsSelect.replaceChildren(...options);
  }

  function updateLevel() {
    levelsSelect.value = model.get("level").toString();
  }

  updateAllLevels();
  model.on("change:all_levels", updateAllLevels);
  updateLevel();
  model.on("change:all_levels", updateLevel);

  levelsSelect.addEventListener("change", () => {
    const value = Number.parseInt(levelsSelect.value, 10);
    model.set("level", value);
    model.save_changes();
  });
}

/** @type { AnyWidget<Traits> } */
export default { render };
