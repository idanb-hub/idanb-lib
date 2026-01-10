from __future__ import annotations

import typing

import solara
from reacton import ipyvuetify

if typing.TYPE_CHECKING:
    import reacton
    import typing_extensions as T


@solara.component
def Link(  # noqa: N802
    text: str,
    url: str,
    *,
    style: str | None = None,
    classes: T.Sequence[str] = (),
) -> reacton.core.Element[T.Any]:
    style = style or ""
    return ipyvuetify.Html(
        tag="a",
        attributes={"href": url},
        class_=" ".join(classes),
        style_=style,
        children=[text],
    )
