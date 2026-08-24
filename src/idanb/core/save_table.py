from __future__ import annotations

import datetime
import functools
from pathlib import Path

import typing_extensions as T
import humanize
import ipymui
import perspective
import structlog
from ipymui.components import mui

from idanb import react

if T.TYPE_CHECKING:
    from idanb.ui.widgets import PerspectiveWidget


_logger = structlog.get_logger()


@react.component
def FileBrowserListItem(  # noqa: N802
    path: Path,
    name: str | None = None,
    **kwargs: T.Unpack[ipymui.Props],
) -> None:
    if name is None:
        name = path.name

    stat = path.stat()

    if path.is_dir():
        details = []
    else:
        details = [
            humanize.naturalsize(stat.st_size),
            humanize.naturalday(datetime.datetime.fromtimestamp(stat.st_mtime)),  # noqa: DTZ006
        ]

    with (
        mui.ListItem(disablePadding=True),
        mui.ListItemButton(**kwargs),
    ):
        with mui.ListItemIcon():
            if path.is_dir():
                mui.icons.Folder()
            else:
                mui.icons.InsertDriveFile()

        mui.ListItemText(primary=name, secondary=" | ".join(details))


@react.component
def FileBrowser(  # noqa: N802
    root: Path,
    on_dir: T.Callable[[Path], None] | None = None,
    on_file: T.Callable[[Path], None] | None = None,
) -> None:
    path, set_path = react.use_state(root)
    cwd = path if path.is_dir() else path.parent

    def on_path() -> None:
        if path.is_dir():
            if on_dir is not None:
                on_dir(path)
        elif on_file is not None:
            on_file(path)

    react.use_effect(on_path, [path])

    with mui.Box():
        with (
            mui.List(
                disablePadding=True,
                dense=True,
            ),
            mui.ListItem(),
        ):
            mui.ListItemText(str(cwd))

        with mui.List(
            disablePadding=True,
            dense=True,
            sx=dict(
                height="30em",
                overflow="auto",
            ),
        ):
            FileBrowserListItem(
                cwd.parent,
                name="..",
                onClick=lambda: set_path(cwd.parent),
            )

            for entry in sorted(
                cwd.iterdir(),
                key=lambda p: (not p.is_dir(), p.name),
            ):
                if entry.name.startswith("."):
                    continue

                FileBrowserListItem(
                    path=entry,
                    onClick=functools.partial(set_path, entry),
                    selected=(path == entry),
                )


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


@react.component
def SaveTablePage(  # noqa: C901 N802 PLR0915
    widget: PerspectiveWidget,
    *,
    savedir: Path | str = ".",
    savename: str = "",
) -> None:
    # We need to know if the widget has data loaded. `PerspectiveWidget.table`
    # cannot be observed (it's a property, not a trait). Instead, we observe
    # `table_name`, which seems to be related.
    # https://github.com/finos/perspective/blob/v3.6.1/rust/perspective-python/perspective/widget/viewer/viewer.py
    table_name, set_table_name = react.use_state(widget.table_name)

    def on_table_name() -> None:
        _logger.debug("table name changed", table_name=table_name)

    react.use_effect(on_table_name, [table_name])

    def on_widget() -> T.Callable[[], None]:
        def on_change(change: dict[str, T.Any]) -> None:
            set_table_name(change["new"])

        widget.observe(on_change, "table_name")
        return lambda: widget.unobserve(on_change, "table_name")

    react.use_effect(on_widget, [widget])

    with mui.Box():
        filedir, set_filedir = react.use_state(Path(savedir))

        FileBrowser(
            root=filedir,
            on_file=lambda path: set_filename(path.name),
            on_dir=set_filedir,
        )

        filename, set_filename = react.use_state(savename)

        def on_filename() -> None:
            fileext = Path(filename).suffix.removeprefix(".").upper()
            if fileext in _TABLE_FORMATS:
                set_filefmt(fileext)

        react.use_effect(on_filename, [filename])

        filefmt, set_filefmt = react.use_state(
            next(iter(_TABLE_FORMATS.keys())),
        )

        def on_filename() -> None:
            fileext = Path(filename).suffix.removeprefix(".").upper()
            if fileext in _TABLE_FORMATS:
                set_filefmt(fileext)

        react.use_effect(on_filename, [filename])

        def on_filefmt() -> None:
            fileext = filefmt.lower()
            set_filename(str(Path(filename).with_suffix(f".{fileext}")))

        react.use_effect(on_filefmt, [filefmt])

        with mui.Grid(container=True, spacing=1):
            with mui.Grid(size=8):
                mui.TextField(
                    label="File name",
                    defaultValue=filename,
                    key=filename,
                    onBlur=ipymui.callback("$[0].target.value")(set_filename),
                    fullWidth=True,
                )

            with mui.Grid(size=4), mui.FormControl(fullWidth=True):
                mui.InputLabel("Format")
                with mui.Select(
                    label="Format",
                    value=filefmt,
                    onChange=ipymui.callback("$[0].target.value")(set_filefmt),
                ):
                    for fmt in _TABLE_FORMATS:
                        mui.MenuItem(fmt, value=fmt)

            def save() -> None:
                filepath = filedir / filename
                kwargs = _TABLE_VIEWS[mode](widget)
                table: perspective.Table = widget.table
                view: perspective.View = table.view(**kwargs)
                try:
                    data = _TABLE_FORMATS[filefmt](view)
                    with filepath.open("w") as f:
                        f.write(data)
                finally:
                    view.delete()

            with mui.Grid(size="grow"):
                mui.Button(
                    "Save",
                    variant="contained",
                    onClick=save,
                    disabled=not bool(table_name),
                    fullWidth=True,
                )

            mode, set_mode = react.use_state(next(iter(_TABLE_VIEWS.keys())))

            with (
                mui.Grid(size="auto"),
                mui.ToggleButtonGroup(
                    exclusive=True,
                    value=mode,
                    onChange=ipymui.callback("$[1]")(set_mode),
                    size="small",
                    color="primary",
                ),
            ):
                for view in _TABLE_VIEWS:
                    mui.ToggleButton(view, value=view)
