from __future__ import annotations

import typing
from pathlib import Path

import perspective.widget
from IPython.display import display_html, display_javascript

if typing.TYPE_CHECKING:
    import typing_extensions as T


_JAVASCRIPT = Path(__file__).with_suffix(".js").read_text(encoding="utf-8")

_HTML = """
<style>
    /* Because custom settings are added before any existing contents. */
    perspective-viewer [slot="plugin-settings"] {
        display: flex;
        flex-direction: row;
    }

    perspective-viewer.maximized {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 9999;
    }
</style>
"""


def init_display() -> None:
    display_html(_HTML, raw=True)
    display_javascript(_JAVASCRIPT, raw=True)


class PerspectiveWidget(perspective.widget.PerspectiveWidget):
    @typing.override
    def _repr_mimebundle_(self, *args: T.Any, **kwargs: T.Any) -> T.Any:
        init_display()
        return super()._repr_mimebundle_(*args, **kwargs)
