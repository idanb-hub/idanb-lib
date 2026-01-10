from __future__ import annotations

import logging
import typing

import anywidget
import structlog
import traitlets

from idanb import utils

if typing.TYPE_CHECKING:
    import typing_extensions as T


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

    _esm = r"""
    import { AnsiUp } from 'https://esm.sh/ansi_up@6';
    const ansi_up = new AnsiUp();

    function render({ model, el }) {
        el.classList.add('widget-logs');
        el.innerHTML = `
            <details class="widget-logs__expandable">
                <summary>
                    Logs
                    <div class="widget-logs__controls">
                        <select class="widget-logs__levels"></select>
                        <button class="widget-logs__clear">clear</button>
                    </div>
                </Summary>
                <pre class="widget-logs__logs"></pre>
            </details>
            <pre class="widget-logs__status"></pre>
        `;

        const logsElement = el.querySelector('.widget-logs__logs');
        const statusElement = el.querySelector('.widget-logs__status');
        const levelsSelect = el.querySelector('select.widget-logs__levels');
        const clearButton = el.querySelector('button.widget-logs__clear');

        clearButton.addEventListener('click', () => {
            logsElement.replaceChildren();
            log('Output has been cleared.\n');
        });

        function log(html) {
            statusElement.innerHTML = html;
            const child = document.createElement('span');
            child.innerHTML = html;
            logsElement.appendChild(child);
        }

        model.on("msg:custom", (msg) => {
            log(ansi_up.ansi_to_html(msg));
        });

        function updateAllLevels() {
            const allLevels = model.get('all_levels');
            const options = Object.entries(allLevels).map(([name, level]) => {
                const option = document.createElement('option');
                option.textContent = name;
                option.value = level;
                return option;
            });
            levelsSelect.replaceChildren(...options);
        }

        function updateLevel() {
            levelsSelect.value = model.get('level').toString();
        }

        updateAllLevels();
        model.on('change:all_levels', updateAllLevels);
        updateLevel();
        model.on('change:all_levels', updateLevel);

        levelsSelect.addEventListener('change', () => {
            const value = Number.parseInt(levelsSelect.value, 10);
            model.set('level', value);
            model.save_changes();
        });
    }

    export default { render };
    """

    _css = r"""
    .widget-logs {
        padding-left: 3px;
    }
    .widget-logs summary {
        font-weight: bold;
    }
    .widget-logs .widget-logs__controls {
        float: right;
    }
    .widget-logs details.widget-logs__expandable[open] ~ .widget-logs__status {
        display: none;
    }
    .widget-logs .widget-logs__status {
        width: 100%;
        overflow: hidden;
        white-space: preserve nowrap;
        text-overflow: ellipsis;
    }
    .widget-logs .widget-logs__logs {
        width: 100%;
        max-height: 30rem;
        overflow: hidden auto;
        white-space: pre-wrap;
        word-break: break-all;
    }
    """

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

    @typing.override
    def close(self) -> None:
        self._logger.removeHandler(self._handler)
        super().close()

    def _log(self, string: str) -> None:
        self.send(string)

    @traitlets.observe("level")
    def _level_changed(self, _change: object) -> None:
        self._handler.setLevel(self.level)
