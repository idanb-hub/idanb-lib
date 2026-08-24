from __future__ import annotations

import logging

import typing_extensions as T
from IPython.core.getipython import get_ipython
from IPython.extensions import autoreload
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from idanb import meta, ui

if T.TYPE_CHECKING:
    from watchdog.events import DirModifiedEvent, FileModifiedEvent


_logger = logging.getLogger(__name__)


def _announce(msg: str, *args: object) -> None:
    msg = msg % args
    print("You are a developer!", msg)  # noqa: T201


def _enable_autoreload() -> None:
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

    _announce(
        "Autoreload magic is enabled. See: %s",
        "https://ipython.readthedocs.io/en/stable/config/extensions/autoreload.html",
    )


class _ReloadWindowEventHandler(FileSystemEventHandler):
    @T.override
    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent) -> None:
        _logger.warning("Notebook file was modified. Reloading window...")
        ui.jsexec("window.location.reload()")


def _reload_page_on_change() -> None:
    handler = _ReloadWindowEventHandler()
    observer = Observer()
    observer.schedule(handler, str(meta.nbpath()), recursive=True)
    observer.start()

    _announce("Window will reload whenever the notebook file changes.")


def devmode() -> None:
    _enable_autoreload()

    if meta.is_voila():
        _reload_page_on_change()
