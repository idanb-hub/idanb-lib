from __future__ import annotations

from analytics.connectors import intelowl
from idanb import meta

from .config import IntelOwlConfig


class IntelOwl(intelowl.IntelOwlConnector):
    def __init__(self, config: intelowl.IntelOwlConfig | None = None) -> None:
        if config is None:
            config = meta.CONFIG[IntelOwlConfig]

        super().__init__(config)
