from __future__ import annotations

import typing

import anywidget
import traitlets

if typing.TYPE_CHECKING:
    import typing_extensions as T


@typing.final
class CopyToClipboard(anywidget.AnyWidget):
    """Copies `data` to clipboard when containing element is clicked.

    The "containing element" is a predecessor `depth` levels higher in the DOM
    (parent is at depth 0, its parent at 1, and so on).
    """

    data = traitlets.Unicode().tag(sync=True)
    depth = traitlets.Int().tag(sync=True)

    def __init__(self, data: str, depth: int = 0, **kwargs: T.Any) -> None:
        super().__init__(data=data, depth=depth, **kwargs)

    _esm = """
    let data = null;

    function handleClick() {
        console.log("Writing text to clipboard:", data)
        navigator.clipboard.writeText(data);
    }

    async function setup(el, depth) {
        // Make sure we're connected to DOM before looking for parent.
        while (!el.isConnected) {
            await new Promise(r => setTimeout(r, 10));
        }

        // AnyWidget adds one extra wrapper element.
        const wrapper = el.parentElement;
        // Turn off display of the wrapper to not affect layout.
        // Style attribute performs better than a broad `:has()` selector.
        wrapper.style.display = "none";

        let parent = wrapper.parentElement;
        for (let i = 0; i < depth; ++i) {
            parent = parent.parentElement;
        }

        parent.addEventListener("click", handleClick);

        return function cleanup() {
            parent.removeEventListener("click", handleClick);
        }
    }

    export default {
        initialize({ model }) {
            function update() { data = model.get("data"); }
            model.on("change:data", update);
            update();
        },
        async render({ model, el }) {
            const depth = model.get("depth");
            const cleanup = await setup(el, depth);

            // Function to be executed when the view is removed.
            return cleanup
        },
    };
    """
