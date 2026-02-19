"""Components for applying custom CSS styles.

This module depends only on `reacton`, `ipywidgets`, and the standard library.
"""

from __future__ import annotations

import os
import sys
import typing
import uuid

import reacton
import reacton.ipywidgets as ipywidgets  # noqa: PLR0402

if typing.TYPE_CHECKING:
    from collections.abc import Mapping

    from reacton.core import Element


def _declarations(declarations: str | Mapping[str, str]) -> str:
    if isinstance(declarations, str):
        return declarations

    return " ".join(f"{prop}: {value};" for prop, value in declarations.items())


def _css(rules: Mapping[str, str | Mapping[str, str]]) -> str:
    return "\n".join(
        f"{selector} {{ {_declarations(declarations)} }}"
        for selector, declarations in rules.items()
    )


@reacton.component
def LocalCSS[Widget: ipywidgets.widgets.DOMWidget](  # noqa: N802
    rules: Mapping[str, str | Mapping[str, str]],
    *,
    container: typing.Callable[..., Element[Widget]] = ipywidgets.Box,
    children: list[typing.Any] = [],  # noqa: B006
) -> Element[Widget]:
    """Applies CSS `rules` to contained elements.

    Args:
        rules: Dictionary whose keys are CSS selectors and values declarations.
        container: Container function component. Must accept `children` kwarg
            and use widget inheriting `ipywidgets.DomWidget`.
        children: List of children to render in the container.

    Returns:
        `container` component inside which `rules` are applied.

    Example:
    ```py
    with LocalCSS({"*": "color: red"}):
        ipywidgets.Label(value="red text")
    ```
    """  # noqa: D401
    unique_class = reacton.use_memo(lambda: f"LocalCSS_{uuid.uuid4().hex}")

    with container(children=children) as parent:
        ipywidgets.HTML(value=f"<style>{_css(rules)}</style>")

    def init() -> None:
        reacton.get_widget(parent).add_class(unique_class)

    reacton.use_effect(init, [])

    return parent


def _detect_notebook_root_selector() -> str | None:
    # Voila
    if "VOILA_REQUEST_URL" in os.environ:
        return "#jp-main-content-panel"

    # The special notebook variables are defined in `__main__`.
    main = sys.modules["__main__"]

    # VSCode
    if "__vsc_ipynb_file__" in vars(main):
        return "body"

    # JupyerLab
    if "__session__" in vars(main):
        return ".jp-NotebookPanel .jp-WindowedPanel-inner"

    return None


@reacton.component
def GlobalCSS(  # noqa: N802
    rules: Mapping[str, str | Mapping[str, str]],
    *,
    root: str | None = None,
) -> Element[typing.Any]:
    """Applies CSS `rules` to current notebook.

    Args:
        rules: Dictionary whose keys are CSS selectors and values declarations.
        root: CSS selector of notebook root element. Autodetected by default.

    Example:
    ```py
    GlobalCSS({"*": "color: red"})
    ipywidgets.Label(value="red text")
    ```
    """  # noqa: D401
    unique_class = reacton.use_memo(lambda: f"GlobalCSS_{uuid.uuid4().hex}")

    if root is None:
        root = _detect_notebook_root_selector()
        if root is None:
            errmsg = "cannot identify notebook environment"
            raise RuntimeError(errmsg)

    rules = {
        f"{root}:has(.{unique_class}) {selector}": declarations
        for selector, declarations in rules.items()
    }

    return ipywidgets.HTML(
        value=f'<style class="{unique_class}">{_css(rules)}</style>',
    )
