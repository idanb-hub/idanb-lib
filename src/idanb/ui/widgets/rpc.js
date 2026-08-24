/** @import { AnyWidget } from "@anywidget/types" */

/** @type { AnyWidget } */
export default {
  initialize({ model }) {
    model.on(
      "msg:custom",
      /** @param {string} msg */
      (msg) => {
        // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/eval#direct_and_indirect_eval
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
        eval?.(msg);
      },
    );
  },
};
