from __future__ import annotations

import pydantic

from analytics.connectors import intelowl
from idanb.utils.config import CONFIG


@CONFIG.register("intelowl")
@pydantic.dataclasses.dataclass()
class IntelOwlConfig(intelowl.IntelOwlConfig):
    pass
