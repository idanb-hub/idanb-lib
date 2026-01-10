from __future__ import annotations

import collections.abc
import html
import typing

import ipyvuetify
import solara
import traitlets
from solara.lab.utils.dataframe import df_columns, df_records

if typing.TYPE_CHECKING:
    import reacton.core
    import typing_extensions as T


@typing.final
class SimpleTableWidget(ipyvuetify.VuetifyTemplate):  # pyright: ignore[reportPrivateImportUsage]
    head = traitlets.List(traitlets.Any()).tag(sync=True)
    body = traitlets.List(traitlets.List(traitlets.Any())).tag(sync=True)
    raw = traitlets.Bool(default_value=False).tag(sync=True)

    @traitlets.default("template")
    def _template(self) -> str:
        return """
            <template>
                <v-simple-table>
                    <thead>
                        <tr>
                            <td v-for="(value, index) in head" :key="index">
                                {{value}}
                            </td>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, index) in body" :key="index">
                            <td v-for="(value, key) in row" :key="key">
                                <span v-if="raw" v-html="value"></span>
                                <span v-else>{{value}}</span>
                            </td>
                        </tr>
                    </tbody>
                </v-simple-table>
            </template>
       """


def infer_columns(data: object) -> T.Sequence[object]:
    try:
        return df_columns(data)
    except TypeError:
        pass

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


@solara.component
def SimpleTable(  # noqa: N802
    data: typing.Any,
    *,
    columns: T.Sequence[object] | None = None,
    head: T.Sequence[str] | None = None,
    raw: bool = False,
) -> reacton.core.Element[SimpleTableWidget]:
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

    try:
        rows = df_records(data)
    except TypeError:
        rows = data

    body = [[r[c] for c in columns] for r in rows]

    return SimpleTableWidget.element(  # pyright: ignore[reportAttributeAccessIssue]
        head=head,
        body=body,
        raw=raw,
    )


@solara.component
def SimpleDictTable[Key](  # noqa: N802
    # Generic because Mapping's key type is invariant.
    data: T.Mapping[Key, object],
    *,
    head: tuple[str, str] | tuple[()] = (),
    raw: bool = False,
) -> reacton.core.Element[SimpleTableWidget]:
    """Small wrapper around `SimpleTable` for displaying dictionaries."""

    dump: T.Callable[[object], str] = (
        str if raw else lambda obj: html.escape(str(obj))
    )

    return SimpleTable(
        data=[(f"<b>{dump(k)}</b>", dump(v)) for k, v in data.items()],
        head=head,
        raw=True,
    )
