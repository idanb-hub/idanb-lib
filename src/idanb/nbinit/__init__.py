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
from datetime import UTC, datetime, timedelta

import structlog
import yaml
from IPython.core.getipython import get_ipython
from IPython.display import display

from idanb import meta, ui
from idanb.core import git

from . import _fix_anywidget_leaks
from ._magic import IdaNBMagics

_logger = logging.getLogger(__name__)


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


def _clear_cache() -> None:
    min_atime = datetime.now(tz=UTC) - timedelta(days=1)
    for path in meta.cachedir().iterdir():
        try:
            if not path.is_file():
                continue
            atime = datetime.fromtimestamp(path.stat().st_atime, tz=UTC)
            if atime < min_atime:
                path.unlink()
        except OSError:
            _logger.exception("Error deleting old cache file %r", path.name)
        else:
            _logger.debug("Deleted old cache file %r", path.name)


def _print_notebook_version() -> None:
    path = meta.nbpath().relative_to(meta.rootdir())

    history = git.follow(path)
    try:
        # Latest commit that modified the notebook.
        commit = next(history)
    except StopIteration:
        version = "??? (file not tracked by git)"
    else:
        count = sum(1 for _ in git.repo().walk(commit.id))
        version = f"{count}#{commit.short_id}"

    print(f"Notebook version: {version}")  # noqa: T201


def nbinit() -> None:
    """Initialize the environment of the executing notebook (`__main__` module).

    See the module docstring for what that entails.
    """
    _print_notebook_version()

    _fix_notebook_module_name()

    _configure_logging()

    _clear_cache()

    _fix_anywidget_leaks.apply_patch()

    ip = get_ipython()
    if ip is not None:
        ip.register_magics(IdaNBMagics)

    ui.rpc.init()

    logs = ui.widgets.Logs()
    display(logs)

    if meta.CONFIG.get("developer") is True:
        from ._devmode import devmode  # noqa: PLC0415

        devmode()


# Run `nbinit()` on import, unless the notebook defines `NBINIT_SKIP = True`.
if vars(sys.modules["__main__"]).get("NBINIT_SKIP") is not True:
    nbinit()


# This uses the updated name if if `nbinit()` was run.
logger = structlog.get_logger(sys.modules["__main__"].__name__)
