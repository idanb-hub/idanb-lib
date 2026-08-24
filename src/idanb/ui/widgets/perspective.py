from __future__ import annotations

import threading
import uuid
from pathlib import Path

import typing_extensions as T
import anywidget
import perspective
import structlog
import traitlets

if T.TYPE_CHECKING:
    import logging

    import polars as pl


_logger: logging.Logger = structlog.get_logger()


# https://docs.rs/perspective-client/4.2.0/perspective_client/config/struct.ViewConfigUpdate.html
class PerspectiveConfig(T.TypedDict, total=False):
    """Configuration for Perspective front-end.

    ```py
    PerspectiveConfig(
        group_by=["CITY"],
        split_by=["BRANCH"],
        columns=["REVENUE", "EXPENSES", "PROFIT", "COUNT"],
        filter=[("PROFIT", ">", 0), ("BRANCH", "is not null", None)],
        sort=[("REVENUE", "desc")],
        expressions={"PROFIT": '"REVENUE" - "EXPENSES"', "COUNT": '"CITY"'},
        aggregates={"COUNT": "count"},
    )
    ```
    """

    group_by: T.Sequence[str]
    split_by: T.Sequence[str]
    columns: T.Sequence[str]
    filter: T.Sequence[tuple[str, str, T.Any]]
    sort: T.Sequence[tuple[str, str]]
    expressions: T.Mapping[str, str]
    aggregates: T.Mapping[str, str]
    group_by_depth: int
    filter_op: T.Literal["And", "Or"]


class PerspectiveWidget(anywidget.AnyWidget):
    _esm: Path = Path(__file__).with_suffix(".js")

    client: perspective.Client
    session: perspective.ProxySession
    table: perspective.Table | None

    table_name: traitlets.Unicode = traitlets.Unicode().tag(sync=True)
    config: traitlets.Dict[str, T.Any] = traitlets.Dict(
        key_trait=traitlets.Unicode(),
    ).tag(sync=True)
    styles: traitlets.Dict[str, str] = traitlets.Dict(
        key_trait=traitlets.Unicode(),
        value_trait=traitlets.Unicode(),
    ).tag(sync=True)
    templates: traitlets.Dict[str, str] = traitlets.Dict(
        key_trait=traitlets.Unicode(),
        value_trait=traitlets.Unicode(),
    ).tag(sync=True)

    def __init__(
        self,
        data: pl.DataFrame | None,
        *,
        styles: T.Mapping[str, str] | None = None,
        templates: T.Mapping[str, str] | None = None,
        **config: T.Unpack[PerspectiveConfig],
    ) -> None:
        self.client = perspective.GLOBAL_CLIENT
        self.session = perspective.ProxySession(
            self.client,
            lambda msg: self.send({"type": "binary_msg"}, [msg]),
        )
        self.table = None

        self.on_msg(type(self).on_custom_msg)

        super().__init__(
            config=config,
            styles=styles or {},
            templates=templates or {},
        )

        if data is not None:
            self.load(data, **config)

    def load(
        self,
        data: pl.DataFrame,
        **config: T.Unpack[PerspectiveConfig],
    ) -> None:
        # Ensure font-end doesn't see changes until ready.
        with self.hold_trait_notifications():
            self.delete()
            self.table_name = uuid.uuid4().hex
            self.table = self.client.table(data, name=self.table_name)
            self.config = dict(config)

    def delete(self) -> None:
        if self.table is None:
            return

        table = self.table
        self.table = None
        table_name = self.table_name
        self.table_name = ""

        def target() -> None:
            # Blocks until all views of this table are destroyed.
            table.delete(lazy=True)
            _logger.debug("Deleted table %s", table_name)

        thread = threading.Thread(target=target)
        thread.start()

    def on_custom_msg(
        self,
        content: dict[str, str],
        buffers: list[bytes],
    ) -> None:
        match content.get("type"):
            case "binary_msg":
                [msg] = buffers
                self.session.handle_request(msg)
            case _ as unknown:
                _logger.warning("unknown message type: %r", unknown)

    @T.override
    def close(self) -> None:
        self.delete()
        super().close()
