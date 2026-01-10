from __future__ import annotations

import asyncio
import contextvars
import typing

if typing.TYPE_CHECKING:
    import typing_extensions as T


_background_tasks: set[asyncio.Task[object]] = set()


class ReturnFromAsyncGenerator(Exception):  # noqa: N818
    """Return a value from an async generator.

    As of Python 3.13, `return` is not supported in async generators.
    This exception can be used instead, but ONLY WHERE THE CALLER EXPECTS IT.

    See:
      [CPython PR: add async generator return value](https://github.com/python/cpython/pull/125401)
    """

    value: T.Any

    def __init__(self, value: T.Any = None) -> None:
        super().__init__(value)
        self.value = value


class ContextProxy[Target]:
    """Transparently wraps an object in a `contextvars.ContextVar`.

    Attribute access is delegated to the wrapped object.
    Methods of `ContextVar` are accessible as static methods.

    ```py
    out = ContextProxy(sys.stdout)
    token = ContextProxy.set(out, sys.stderr)
    out.write("this goes to stderr")
    ContextProxy.reset(token)
    out.write("this goes to stdout")
    ```

    Forwarding of dunder methods is not implemented.
    """

    _target: contextvars.ContextVar[Target]

    if typing.TYPE_CHECKING:
        # This makes `ContextProxy` appear transparent to type-checkers.
        def __new__(cls, target: Target) -> Target: ...

    def __init__(self, target: Target) -> None:
        if isinstance(target, ContextProxy):
            errmsg = f"target {target!r} is already wrapped in {ContextProxy.__name__}"
            raise TypeError(errmsg) from None
        self._target = contextvars.ContextVar("_target", default=target)

    @staticmethod
    def target[Target_](
        instance: ContextProxy[Target_],
    ) -> contextvars.ContextVar[Target_]:
        return object.__getattribute__(instance, "_target")

    @staticmethod
    def get[Target_](
        instance: ContextProxy[Target_],
    ) -> Target_:
        return __class__.target(instance).get()

    @staticmethod
    def set[Target_](
        instance: ContextProxy[Target_],
        value: Target_,
    ) -> contextvars.Token[Target_]:
        return __class__.target(instance).set(value)

    @staticmethod
    def reset[Target_](
        instance: ContextProxy[Target_],
        token: contextvars.Token[Target_],
    ) -> None:
        return __class__.target(instance).reset(token)

    @typing.override
    def __getattribute__(self, attr: str) -> T.Any:
        return getattr(type(self).get(self), attr)
