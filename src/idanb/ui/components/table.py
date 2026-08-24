from __future__ import annotations

import collections.abc
import html

import typing_extensions as T
from ipymui.components import mui

from idanb import react

if T.TYPE_CHECKING:
    import polars as pl


def get_module(obj: object) -> str:
    return obj.__class__.__module__.split(".", maxsplit=1)[0]


def is_polars(obj: object) -> T.TypeIs[pl.DataFrame]:
    if get_module(obj) != "polars":
        return False

    import polars as pl  # noqa: PLC0415

    return isinstance(obj, pl.DataFrame)


def infer_columns(data: object) -> T.Sequence[object]:
    if is_polars(data):
        return data.columns

    if not isinstance(data, collections.abc.Collection):
        errmsg = "invalid data, must be either DataFrame or Collection"
        raise TypeError(errmsg)

    it = iter(data)
    try:
        item = next(it)
    except StopIteration:
        errmsg = "cannot infer column names from empty data"
        raise ValueError(errmsg) from None

    if isinstance(item, collections.abc.Mapping):
        return list(item.keys())

    if isinstance(item, collections.abc.Sequence):
        return list(range(len(item)))

    errmsg = "invalid data, must contain either Mappings or Sequences"
    raise TypeError(errmsg)


@react.component
def SimpleTable(  # noqa: N802
    data: T.Any,
    *,
    columns: T.Sequence[object] | None = None,
    head: T.Sequence[str] | None = None,
    raw: bool = False,
) -> react.Element[T.Any]:
    """Simple static table that displays given data.

    Args:
        data: Table contents as either a DataFrame or a list of rows/records.
        columns: Columns of `data` to display. Defaults to all columns.
        head: Displayed column headings. Defaults to `columns`.
        raw: Whether to render `data` as HTML (`True`) or plaintext (`False`).
    """  # noqa: D401

    if columns is None:
        columns = infer_columns(data)

    if head is None:
        head = list(map(str, columns))

    rows: T.Any = data.to_dicts() if is_polars(data) else data

    body = [[r[c] for c in columns] for r in rows]

    with mui.TableContainer() as container, mui.Table():
        with mui.TableHead(), mui.TableRow():
            for column in head:
                mui.TableCell(column)
        with mui.TableBody():
            for row in body:
                with mui.TableRow():
                    for cell in row:
                        if raw:
                            mui.TableCell(
                                dangerouslySetInnerHTML=dict(__html=cell),
                            )
                        else:
                            mui.TableCell(cell)

    return container


@react.component
def SimpleDictTable[Key](  # noqa: N802
    # Generic because Mapping's key type is invariant.
    data: T.Mapping[Key, object],
    *,
    head: tuple[str, str] | tuple[()] = (),
    raw: bool = False,
) -> react.Element[T.Any]:
    """Small wrapper around `SimpleTable` for displaying dictionaries."""

    dump: T.Callable[[object], str] = (
        str if raw else lambda obj: html.escape(str(obj))
    )

    return SimpleTable(
        data=[(f"<b>{dump(k)}</b>", dump(v)) for k, v in data.items()],
        head=head,
        raw=True,
    )
