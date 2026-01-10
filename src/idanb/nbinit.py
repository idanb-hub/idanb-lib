"""Inject our common setup into a notebook's environment.

Use the `%run -n` magic command to source this script at the beginning of your
notebook.

What this script does:

1. Adds the `src/` directory to `sys.path`, if it's not there already.
1. Fixes the notebook's module name to enable relative imports.
1. Configures logging and displays `idanb.widgets.Logs` widget.
"""

# ruff: noqa: PLC0415

from __future__ import annotations

import logging
import logging.config
import os
import sys
import urllib.parse
from pathlib import Path

import structlog
import yaml
from IPython.core.getipython import get_ipython
from IPython.display import display

logger = structlog.get_logger()


def _find_notebook_path() -> Path:
    # The main module is the notebook itself.
    main = sys.modules["__main__"]

    voila_url = os.environ.get("VOILA_REQUEST_URL")
    if voila_url is not None:
        # Combine filename from the URL and CWD to get the notebook path.
        url_path = urllib.parse.urlsplit(voila_url).path
        return Path.cwd() / Path(url_path).name

    # Variables which might contain the notebook path.
    path_vars = [
        "__session__",  # JupyterLab
        "__vsc_ipynb_file__",  # VS Code
    ]

    path = next(filter(None, map(vars(main).get, path_vars)), None)
    if path is None:
        errmsg = "could not determine notebook path"
        raise RuntimeError(errmsg)

    return Path(path)


nbpath = _find_notebook_path()


def _find_root_directory() -> Path:
    for parent in nbpath.parents:
        if parent.joinpath("pyproject.toml").is_file():
            return parent

    errmsg = "could not determine project root"
    raise FileNotFoundError(errmsg)


rootdir = _find_root_directory()


def nbinit() -> None:
    # The main module is the notebook itself.
    main = sys.modules["__main__"]

    # Prepend "/src" directory to `sys.path`.
    srcdir = str(rootdir / "src")
    if srcdir not in sys.path:
        sys.path.insert(0, srcdir)

    # Set notebook's module name (this enables relative imports).
    basedir = next(filter(nbpath.is_relative_to, (srcdir, rootdir)), None)
    if basedir is None:
        errmsg = "could not determine notebook module name"
        raise RuntimeError(errmsg)
    name = ".".join(nbpath.relative_to(basedir).with_suffix("").parts)
    main.__name__ = name
    sys.modules[name] = main

    # Set up logging.
    with (rootdir / "config" / "logging.yaml").open() as f:
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

    from idanb import widgets

    logs = widgets.Logs()
    display(logs)

    # Load config.
    from idanb.utils.config import configure

    # Reload the global config every time this script is executed.
    config = configure()

    # Load and enable autoreload if "developer" config option is set.
    if config.get("developer") is True:
        from IPython.extensions import autoreload

        ip = get_ipython()
        if ip is None:
            errmsg = "couldn't get current IPython instance"
            raise RuntimeError(errmsg)
        if ip.extension_manager is None:
            errmsg = "current IPython instance is missing an extension manager"
            raise RuntimeError(errmsg)

        if autoreload.__name__ not in ip.extension_manager.loaded:
            ip.extension_manager.load_extension(autoreload.__name__)

        ip.run_line_magic("autoreload", "complete")
        print(  # noqa: T201
            "You are a developer! Autoreload is enabled.",
            "https://ipython.readthedocs.io/en/stable/config/extensions/autoreload.html",
            sep="\n",
        )
