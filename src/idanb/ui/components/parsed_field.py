from __future__ import annotations

import typing_extensions as T
import ipymui
from ipymui.components import mui

from idanb import react


@react.component
def ParsedField[Parsed](  # noqa: N802
    label: str,
    *,
    value: Parsed,
    on_value: T.Callable[[Parsed], None],
    parser: T.Callable[[str], Parsed],
    init_value: str | None = None,
    **kwargs: T.Unpack[ipymui.Props],
) -> react.Element[T.Any]:
    init_value = react.use_memo(
        lambda: init_value if init_value is not None else str(value),
        dependencies=[],
    )

    error, set_error = react.use_state[Exception | None](None)

    @ipymui.callback("$[0].target.value")
    def set_value(value: str) -> None:
        try:
            parsed = parser(value)
        except Exception as e:  # noqa: BLE001
            set_error(e)
        else:
            on_value(parsed)
            set_error(None)

    react.use_memo(lambda: set_value(init_value), dependencies=[])

    return mui.TextField(
        label=label,
        defaultValue=init_value,
        onBlur=set_value,
        error=error is not None,
        helperText=str(error) if error is not None else "",
        **kwargs,
    )
