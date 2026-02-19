from __future__ import annotations

from IPython.display import display

from .widgets import RPC


def init() -> RPC:
    global rpc  # noqa: PLW0603

    if rpc is None:
        rpc = RPC()

    if not rpc._view_count:  # noqa: SLF001
        display(rpc)

    return rpc


def send(expr: str) -> None:
    """Evaluate `expr` as a JavaScript expression on the frontend."""
    init().send(expr)


rpc: RPC | None = None
