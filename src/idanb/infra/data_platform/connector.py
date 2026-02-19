from __future__ import annotations

import itertools
import typing

from analytics.connectors.trino import TrinoConnector
from idanb.utils.config import CONFIG

from .config import Catalog, DataPlatformConfig, Host
from .tables import rows_to_polars

if typing.TYPE_CHECKING:
    import polars as pl
    import typing_extensions as T

    from analytics.connectors.trino import TrinoQuery


class QueryProgress:
    state: str
    progress: float
    url: str

    def __init__(self, query: TrinoQuery) -> None:
        if query.cursor.info_uri is None:
            raise ValueError
        self.url = query.cursor.info_uri

        stats = query.stats

        state = stats["state"]
        if not isinstance(state, str):
            raise TypeError
        self.state = state

        total = stats.get("totalSplits", 0)
        if not isinstance(total, int):
            raise TypeError
        completed = stats.get("completedSplits", 0)
        if not isinstance(completed, int):
            raise TypeError

        self.progress = completed / total * 100 if total > 0 else 0


class DataPlatform:
    connectors: dict[tuple[Host, Catalog], TrinoConnector]

    def __init__(self, config: DataPlatformConfig | None = None) -> None:
        if config is None:
            config = CONFIG[DataPlatformConfig]

        self.connectors = {
            matrix: TrinoConnector(config.select(*matrix))
            for matrix in itertools.product(Host, Catalog)
        }

    async def execute(
        self,
        query: str,
        *params: object,
        host: Host = Host.SHORT_QUERIES,
        catalog: Catalog = Catalog.FLOWS,
        on_progress: T.Callable[[QueryProgress], None] | None = None,
    ) -> pl.DataFrame:
        connector = self.connectors[host, catalog]
        pages: list[list[list[object]]] = []

        if on_progress is None:
            on_progress = lambda _: None  # noqa: E731

        async with connector.execute(query, *params) as results:
            on_progress(QueryProgress(results))
            async for page in results.pages():
                on_progress(QueryProgress(results))
                if not page:
                    continue
                pages.append(page)

        types: dict[str, str] = {}
        for col in await results.schema():
            # For some reason, `type_code` holds the type name (string),
            # even though it's annotated as an int.
            if not isinstance(col.type_code, str):
                errmsg = "this used to be string (when it shouldn't)"
                raise TypeError(errmsg)
            types[col.name] = col.type_code.lower()

        return rows_to_polars(
            itertools.chain.from_iterable(pages),
            types,
        )
