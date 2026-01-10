from __future__ import annotations

import asyncio
import collections.abc
import typing

import ipywidgets

from idanb import utils

if typing.TYPE_CHECKING:
    import typing_extensions as T


class OnClickParams(typing.TypedDict, total=False):
    clear: bool


class Button(ipywidgets.Button):
    _pending_calls: int
    _pending_tasks: set[asyncio.Task[None]]
    __callbacks: list[T.Callable[[T.Self], object]]

    def __init__(self, *args: T.Any, **kwargs: T.Any) -> None:
        super().__init__(*args, **kwargs)
        self._pending_calls = 0
        self._pending_tasks = set()
        self.__callbacks = []

    @typing.overload
    def on_click(
        self,
        callback: T.Callable[[T.Self], None | T.Awaitable[None]],
        /,
        **kwargs: T.Unpack[OnClickParams],
    ) -> None: ...

    @typing.overload
    def on_click[R: (None, T.Awaitable[None])](
        self,
        /,
        **kwargs: T.Unpack[OnClickParams],
    ) -> T.Callable[
        [T.Callable[[T.Self], R]],
        T.Callable[[T.Self], R],
    ]: ...

    @typing.override
    def on_click(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        callback: T.Callable[[T.Self], None | T.Awaitable[None]] | None = None,
        /,
        **kwargs: T.Unpack[OnClickParams],
    ) -> T.Any:
        if callback is None:

            def decorator(func: T.Callable[[T.Self], None]) -> T.Any:
                self.on_click(func)
                return func

            return decorator

        if kwargs.get("clear", False):
            for cb in self.__callbacks:
                super().on_click(cb, remove=True)

        callback = self._wrap_callback(callback, **kwargs)

        def wrapped(btn: T.Self) -> None:
            result = callback(btn)
            if isinstance(result, collections.abc.Coroutine):
                task = asyncio.create_task(result)
                self._pending_tasks.add(task)
                task.add_done_callback(self._pending_tasks.remove)

        self.__callbacks.append(wrapped)
        super().on_click(wrapped)
        return None

    def _wrap_callback(
        self,
        callback: T.Callable[[T.Self], None | T.Awaitable[None]],
        **_kwargs: T.Unpack[OnClickParams],
    ) -> T.Callable[[T.Self], None | T.Awaitable[None]]:
        @utils.decorator.universaldecorator
        def decorator(_args: object, _kwargs: object) -> T.Generator[object]:
            self.disabled = True
            self._pending_calls += 1
            try:
                return (yield)
            finally:
                self._pending_calls -= 1
                if self._pending_calls == 0:
                    self.disabled = False

        return decorator(callback)
