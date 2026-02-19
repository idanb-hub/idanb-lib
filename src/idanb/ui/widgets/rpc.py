from __future__ import annotations

from pathlib import Path

import anywidget


class RPC(anywidget.AnyWidget):
    _esm = Path(__file__).with_suffix(".js")
