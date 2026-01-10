from __future__ import annotations

import typing

import solara

if typing.TYPE_CHECKING:
    import typing_extensions as T


def use_component[**P](
    factory: T.Callable[P, object],
    *args: P.args,
    **kwargs: P.kwargs,
) -> solara.Reactive[T.Any]:
    if "value" in kwargs:
        value = solara.use_reactive(kwargs["value"])
        kwargs["value"] = value
    elif "values" in kwargs:
        value = solara.use_reactive(kwargs["values"])
        kwargs["values"] = value
    else:
        errmsg = "neither 'value' nor 'values' keyword argument was given"
        raise ValueError(errmsg)

    _ = factory(*args, **kwargs)
    return value
