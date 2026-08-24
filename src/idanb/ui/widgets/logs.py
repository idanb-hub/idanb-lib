from __future__ import annotations

import logging
from pathlib import Path

import typing_extensions as T
import anywidget
import structlog
import traitlets

from idanb import utils

_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class Logs(anywidget.AnyWidget):
    level = traitlets.Int(default_value=logging.NOTSET).tag(sync=True)
    all_levels = traitlets.Dict(default_value=_LOG_LEVELS).tag(sync=True)

    # TODO: Maybe limit number of displayed logs?
    # TODO: Ensure `ansi_up` integrity or serve it ourselves.

    _esm = Path(__file__).with_suffix(".js")
    _css = Path(__file__).with_suffix(".css")

    def __init__(self, name: str | None = None, **kwargs: T.Any) -> None:
        """Create a widget that displays log output.

        Args:
            name: Name of logger to capture (as in `logging.getLogger()`).
            kwargs: Forwarded to widget's `__init__`.
        """

        self._logger = logging.getLogger(name)
        self._handler = self._create_handler()
        self._logger.addHandler(self._handler)

        super().__init__(**kwargs)

    def _create_handler(self) -> logging.Handler:
        stream = utils.iotools.TextIOAdapter(write=self._log)
        handler = logging.StreamHandler(stream)

        # Use `structlog` to format logged messages.
        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            ],
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
        )
        handler.setFormatter(formatter)

        return handler

    @T.override
    def close(self) -> None:
        self._logger.removeHandler(self._handler)
        super().close()

    def _log(self, string: str) -> None:
        self.send(string)

    @traitlets.observe("level")
    def _level_changed(self, _change: object) -> None:
        self._handler.setLevel(self.level)
