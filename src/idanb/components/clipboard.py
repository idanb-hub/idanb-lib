from __future__ import annotations

import typing

import solara

from idanb import widgets

if typing.TYPE_CHECKING:
    import reacton
    import typing_extensions as T


@solara.component
def CopyToClipboard(  # noqa: N802
    data: str,
    depth: int = 0,
) -> reacton.core.Element[widgets.CopyToClipboard]:
    """Copies `data` to clipboard when containing element is clicked.

    The "containing element" is a predecessor `depth` levels higher in the DOM
    (parent is at depth 0, its parent at 1, and so on).

    ```py
    text = "Lorem ipsum dolor sit amet ..."
    with solara.Row():
        Clipboard(data=text)
        solara.Text(text)
    ```
    """  # noqa: D401
    return widgets.CopyToClipboard.element(data=data, depth=depth)  # pyright: ignore[reportAttributeAccessIssue]


@solara.component
def ClipboardButton(  # noqa: N802
    *,
    data: str,
    **kwargs: T.Any,
) -> reacton.core.Element[T.Any]:
    """Same as `solara.Button` but copies `data` to clipboard when clicked."""  # noqa: D401
    with solara.Button(**kwargs) as btn:
        # Increased depth because button content is inside one extra wrapper.
        CopyToClipboard(data=data, depth=1)
    return btn
