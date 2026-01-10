from __future__ import annotations

import typing

import solara
import solara.lab

if typing.TYPE_CHECKING:
    import ipyvuetify
    import reacton.core
    import typing_extensions as T


class ButtonParams(typing.TypedDict, total=False):
    label: str
    icon_name: str
    disabled: bool
    text: bool
    outlined: bool
    color: str | None
    classes: list[str]
    style: str | dict[str, str] | None


@solara.component
def TaskButton[**P, R](  # noqa: N802, PLR0913
    task: solara.lab.Task[P, R],
    *,
    if_not_called: ButtonParams = {},  # noqa: B006
    if_pending: ButtonParams = {},  # noqa: B006
    if_finished: ButtonParams = {},  # noqa: B006
    if_error: ButtonParams = {},  # noqa: B006
    if_cancelled: ButtonParams = {},  # noqa: B006
    **kwargs: typing.Unpack[ButtonParams],
) -> reacton.core.ValueElement[ipyvuetify.Btn, T.Any]:
    """Button for controlling tasks.

    On click, the task is started if not pending, otherwise cancelled.
    The `if_*` arguments override kwargs while task is in corresponding state.
    """
    if task.not_called:
        kwargs.update(if_not_called)
    elif task.pending:
        kwargs.update(if_pending)
    elif task.finished:
        kwargs.update(if_finished)
    elif task.error:
        kwargs.update(if_error)
    elif task.cancelled:
        kwargs.update(if_cancelled)

    return solara.Button(
        on_click=task.cancel if task.pending else task,
        **kwargs,
    )
