"""Components for applying custom CSS styles.

This module depends only on `solara` and the standard library.
"""

from __future__ import annotations

import os
import sys
import typing

import solara

if typing.TYPE_CHECKING:
    from collections.abc import Mapping

    import reacton.core


def _declarations(declarations: str | Mapping[str, str]) -> str:
    if isinstance(declarations, str):
        return declarations

    return " ".join(f"{prop}: {value};" for prop, value in declarations.items())


def _css(rules: Mapping[str, str | Mapping[str, str]]) -> str:
    return "\n".join(
        f"{selector} {{ {_declarations(declarations)} }}"
        for selector, declarations in rules.items()
    )


@solara.component
def LocalCSS[Element: reacton.core.Element[typing.Any]](  # noqa: N802
    rules: Mapping[str, str | Mapping[str, str]],
    *,
    container: typing.Callable[..., Element] = solara.Column,
    children: list[typing.Any] = [],  # noqa: B006
) -> Element:
    """Applies CSS `rules` to contained elements.

    Args:
        rules: Dictionary whose keys are CSS selectors and values declarations.
        container: Container function component. Must accept kwargs `children`
            and `classes`. Defaults to `solara.Column`.
        children: List of children to render in the container.

    Returns:
        `container` component inside which `rules` are applied.

    Example:
    ```py
    with LocalCSS({"*": "color: red"}):
        solara.Text("red text")
    ```
    """  # noqa: D401
    unique_class = solara.use_unique_key(prefix="LocalCSS_")

    with container(children=children, classes=[unique_class]) as parent:
        solara.HTML("style", _css(rules))

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


@solara.component
def GlobalCSS(  # noqa: N802
    rules: Mapping[str, str | Mapping[str, str]],
    *,
    root: str | None = None,
) -> reacton.core.Element[typing.Any]:
    """Applies CSS `rules` to current notebook.

    Args:
        rules: Dictionary whose keys are CSS selectors and values declarations.
        root: CSS selector of notebook root element. Autodetected by default.

    Example:
    ```py
    GlobalCSS({"*": "color: red"})
    solara.Text("red text")
    ```
    """  # noqa: D401
    unique_class = solara.use_unique_key(prefix="GlobalCSS_")

    if root is None:
        root = _detect_notebook_root_selector()
        if root is None:
            errmsg = "cannot identify notebook environment"
            raise RuntimeError(errmsg)

    rules = {
        f"{root}:has(.{unique_class}) {selector}": declarations
        for selector, declarations in rules.items()
    }

    return solara.HTML("style", _css(rules), classes=[unique_class])
