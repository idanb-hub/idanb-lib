from __future__ import annotations

import typing
from datetime import datetime

import solara
import solara.lab

if typing.TYPE_CHECKING:
    import typing_extensions as T


@solara.component
def InputDateTime(  # noqa: N802
    value: datetime | solara.Reactive[datetime],
    on_value: T.Callable[[datetime], None] | None = None,
    label: str = "Pick a datetime",
    **kwargs: T.Any,
) -> None:
    value = solara.use_reactive(value, on_value)

    time_open = solara.use_reactive(False)
    date_open = solara.use_reactive(False)

    def update() -> None:
        value.set(datetime.combine(date.get(), time.get(), value.get().tzinfo))

    def on_date(_value: object) -> None:
        update()
        time_open.set(True)

    def on_time(_value: object) -> None:
        update()

    date = solara.use_reactive(value.get().date(), on_date)
    time = solara.use_reactive(value.get().time(), on_time)

    solara.Style("""
        .datetime-picker__date, .datetime-picker__time {
            max-width: unset !important;
            min-width: unset !important;
            width: 50%;
        }
        .datetime-picker__date {
            order: 0;
        }
        .datetime-picker__time {
            transform: translateX(-100%);
            order: 1;
        }
        .datetime-picker__time .v-input__slot {
            transform: translateX(100%);
        }
        /* Hide the date picker icon. */
        .datetime-picker__date .v-input__append-inner {
            display: none;
        }
    """)

    with solara.Row(gap="0px", **kwargs):
        solara.lab.InputTime(
            value=time,  # pyright: ignore[reportArgumentType]
            open_value=time_open,
            label="",
            classes=["datetime-picker__time"],
        )
        solara.lab.InputDate(
            value=date,  # pyright: ignore[reportArgumentType]
            open_value=date_open,
            label=label,
            classes=["datetime-picker__date"],
        )
