"""Notebook environment initialization.

The first cell of every notebook should be:

```py
from __future__ import annotations

from idanb.nbinit import logger
```

On import, this module:

1. Fixes the notebook's module name to enable relative imports.
1. Configures logging and displays a `idanb.ui.widgets.Logs` widget.
1. Enables development extensions if developer mode is enabled.
"""

from __future__ import annotations

import logging
import logging.config
import sys

import structlog
import yaml
from IPython.display import display

from idanb import meta, ui, utils

from . import _fix_anywidget_leaks


def _fix_notebook_module_name() -> None:
    """Fix the notebook's module name to enable relative imports."""
    # The main module is the notebook itself.
    main = sys.modules["__main__"]

    relpath = meta.nbpath().relative_to(meta.rootdir())
    name = ".".join(relpath.with_suffix("").parts)
    main.__name__ = name

    # Make the notebook module accessible under its new name.
    sys.modules[name] = main


def _configure_logging() -> None:
    with (meta.rootdir() / "config" / "logging.yaml").open() as f:
        logging.config.dictConfig(yaml.safe_load(f))

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def nbinit() -> None:
    """Initialize the environment of the executing notebook (`__main__` module).

    See the module docstring for what that entails.
    """
    # Reload the global config every time this script is executed.
    config = utils.config.configure()

    _fix_notebook_module_name()

    _configure_logging()

    _fix_anywidget_leaks.apply_patch()

    ui.rpc.init()

    logs = ui.widgets.Logs()
    display(logs)

    if config.get("developer") is True:
        from ._devmode import devmode  # noqa: PLC0415

        devmode()


# Run `nbinit()` on import, unless the notebook defines `NBINIT_SKIP = True`.
if vars(sys.modules["__main__"]).get("NBINIT_SKIP") is not True:
    nbinit()


# This uses the updated name if if `nbinit()` was run.
logger = structlog.get_logger(sys.modules["__main__"].__name__)
