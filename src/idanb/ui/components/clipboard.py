from __future__ import annotations

import typing

import reacton
from ipymui.components import mui

from idanb.ui.widgets import CopyToClipboard as CopyToClipboardWidget

if typing.TYPE_CHECKING:
    import typing_extensions as T
    from reacton.core import Element


@reacton.component
def CopyToClipboard(  # noqa: N802
    data: str,
    depth: int = 0,
) -> Element[CopyToClipboardWidget]:
    """Copies `data` to clipboard when containing element is clicked.

    The "containing element" is a predecessor `depth` levels higher in the DOM
    (parent is at depth 0, its parent at 1, and so on).

    ```py
    text = "Lorem ipsum dolor sit amet ..."
    with Box():
        CopyToClipboard(data=text)
        Text(text)
    ```
    """  # noqa: D401
    return CopyToClipboardWidget.element(data=data, depth=depth)  # pyright: ignore[reportAttributeAccessIssue]


@reacton.component
def ClipboardButton(  # noqa: N802
    *,
    data: str,
    **kwargs: T.Any,
) -> Element[T.Any]:
    """Same as `mui.Button` but copies `data` to clipboard when clicked."""  # noqa: D401
    with mui.Button(**kwargs) as btn:
        # Increased depth because button content is inside one extra wrapper.
        CopyToClipboard(data=data, depth=1)
    return btn
