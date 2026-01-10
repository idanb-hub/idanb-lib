from __future__ import annotations

import typing
from pathlib import Path

import perspective
import solara
import structlog

from idanb.components import use_component

if typing.TYPE_CHECKING:
    import typing_extensions as T
    from perspective.widget import PerspectiveWidget


_logger = structlog.get_logger()


# Functions that extract kwargs for `perspective.Table.view` from a widget.
_TABLE_VIEWS: dict[str, T.Callable[[PerspectiveWidget], dict[str, T.Any]]] = {
    "Table": lambda _: {},
    "View": lambda widget: {
        field: getattr(widget, field)
        # Fields from Rust API. Is there a way to get them programmatically?
        # https://docs.rs/perspective-client/3.6.1/perspective_client/config/struct.ViewConfigUpdate.html
        for field in [
            "group_by",
            "split_by",
            "columns",
            "filter",
            "filter_op",
            "sort",
            "expressions",
            "aggregates",
            "group_by_depth",
        ]
        if hasattr(widget, field)
    },
}

# Functions that serialize `perspective.View`.
_TABLE_FORMATS: dict[str, T.Callable[[perspective.View], str]] = {
    "CSV": perspective.View.to_csv,
    "JSON": perspective.View.to_json_string,
}


@solara.component
def SaveTablePage(  # noqa: N802
    widget: PerspectiveWidget,
    *,
    savedir: Path | str = ".",
    savename: str = "",
) -> None:
    # We need to know if the widget has data loaded. `PerspectiveWidget.table`
    # cannot be observed (it's a property, not a trait). Instead, we observe
    # `table_name`, which seems to be related.
    # https://github.com/finos/perspective/blob/v3.6.1/rust/perspective-python/perspective/widget/viewer/viewer.py
    table_name: solara.Reactive[str | None] = solara.use_reactive(
        widget.table_name,
        on_change=lambda v: _logger.debug("table name changed", table_name=v),
    )
    solara.use_memo(
        lambda: widget.observe(
            lambda change: table_name.set(change["new"]),
            "table_name",
        )
    )

    filedir = solara.use_reactive(Path(savedir))
    solara.FileBrowser(
        directory=filedir,
        can_select=False,
        on_file_open=lambda path: filename.set(path.name),
        on_directory_change=filedir.set,
    )

    with solara.Row():
        filename = use_component(
            solara.InputText,
            value=savename,
            label="File name",
            style="flex: 2",
        )

        def on_filename(value: str) -> None:
            fileext = Path(value).suffix.removeprefix(".").upper()
            if fileext in _TABLE_FORMATS:
                filefmt.set(fileext)

        filename.subscribe(on_filename)

        filefmt = use_component(
            solara.Select,
            values=list(_TABLE_FORMATS.keys()),
            value=next(iter(_TABLE_FORMATS.keys())),
            label="Format",
            style="flex: 1",
        )

    def save() -> None:
        filepath = filedir.peek() / filename.peek()
        kwargs = _TABLE_VIEWS[mode.peek()](widget)
        table: perspective.Table = widget.table
        view: perspective.View = table.view(**kwargs)
        try:
            data = _TABLE_FORMATS[filefmt.peek()](view)
            with filepath.open("w") as f:
                f.write(data)
        finally:
            view.delete()

    with solara.Row():
        solara.Button(
            label="Save",
            color="primary",
            on_click=save,
            disabled=table_name.get() is None,
            style="flex: 1",
        )

        mode = use_component(
            solara.ToggleButtonsSingle,
            values=list(_TABLE_VIEWS.keys()),
            value=next(iter(_TABLE_VIEWS.keys())),
            dense=True,
        )
