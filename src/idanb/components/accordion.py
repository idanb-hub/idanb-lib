from __future__ import annotations

import typing

import solara
from reacton import ipyvuetify

if typing.TYPE_CHECKING:
    import reacton
    import typing_extensions as T


@solara.component
def Accordion(  # noqa: N802
    expand: int | None | solara.Reactive[int | None] = None,
    children: list[typing.Any] = [],  # noqa: B006
) -> reacton.core.Element[T.Any]:
    """Accordion primary component.

    Like `solara.Details`, but contains multiple expandables (`AccordionItem`),
    of which only one can be expanded at any given time.

    Args:
        expand: Index of expanded child (or `None` to collapse all).
        children: List of children components.

    Returns:
        Root `ipyvuetify.ExpansionPanels` component.

    Example:
    ```py
    with Accordion(expand=0):
        with AccordionItem(header="foo"):
            ...
        with AccordionItem(header="bar"):
            ...
    ```
    """
    expand = solara.use_reactive(expand)

    return ipyvuetify.ExpansionPanels(
        children=children,
        v_model=expand.get(),
        on_v_model=expand.set,
    )


@solara.component
def AccordionItem(  # noqa: N802
    header: str,
    children: list[typing.Any] = [],  # noqa: B006
) -> reacton.core.Element[T.Any]:
    """Accordion child component.

    See `Accortion`.

    Args:
        header: Header of the expandable section.
        children: List of children components.

    Returns:
        `ipyvuetify.ExpansionPanel` container component.
    """
    with ipyvuetify.ExpansionPanel() as container:
        ipyvuetify.ExpansionPanelHeader(children=[header])
        ipyvuetify.ExpansionPanelContent(children=children)

    return container
