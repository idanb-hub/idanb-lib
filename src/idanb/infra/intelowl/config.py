from __future__ import annotations

import pydantic

from analytics.connectors import intelowl
from idanb import meta


@meta.CONFIG.register("intelowl")
@pydantic.dataclasses.dataclass()
class IntelOwlConfig(intelowl.IntelOwlConfig):
    pass
