from __future__ import annotations

import typing

import solara

if typing.TYPE_CHECKING:
    import ipyvuetify
    import reacton
    import typing_extensions as T


@solara.component
def InputParsed[Parsed](  # noqa: N802, PLR0913
    label: str,
    *,
    value: solara.Reactive[Parsed],
    on_value: T.Callable[[Parsed], None] | None = None,
    parser: T.Callable[[str], Parsed],
    init: str | None = None,
    error: solara.Reactive[Exception | None] | None = None,
    on_error: T.Callable[[Exception | None], None] | None = None,
    **kwargs: T.Any,
) -> reacton.core.Element[ipyvuetify.TextField]:
    value = solara.use_reactive(value, on_value)
    error = solara.use_reactive(error, on_error)
    init = solara.use_memo(
        lambda: init if init is not None else str(value.peek())
    )

    def on_value(new: str) -> None:
        try:
            parsed = parser(new)
        except Exception as e:  # noqa: BLE001
            error.set(e)
        else:
            value.set(parsed)
            error.set(None)

    solara.use_memo(lambda: on_value(init))

    return solara.InputText(
        label=label,
        value=init,
        on_value=on_value,
        error=str(error.get()) or True if error.get() is not None else False,
        **kwargs,
    )
