from __future__ import annotations

import abc
import functools
import inspect

import typing_extensions as T

from .asynctools import ReturnFromAsyncGenerator
from .typeutils import copy_signature_from


class UniversalDecorator(abc.ABC):
    """Decorator that supports all functions (async and/or generators).

    This relies `inspect.is*function()` to detect what kind of function is
    being decorated, which takes only the function's definition into account.
    To decorate callable objects or plain functions returning
    generators/awaitables, use the appropriate `.decorate_*()` method directly.
    """

    @abc.abstractmethod
    def decorate_sync[R, **P](
        self,
        func: T.Callable[P, R],
    ) -> T.Callable[P, R]: ...

    @abc.abstractmethod
    def decorate_gen[Y, S, R, **P](
        self,
        func: T.Callable[P, T.Generator[Y, S, R]],
    ) -> T.Callable[P, T.Generator[Y, S, R]]: ...

    @abc.abstractmethod
    def decorate_async[R, **P](
        self,
        func: T.Callable[P, T.Awaitable[R]],
    ) -> T.Callable[P, T.Awaitable[R]]: ...

    @abc.abstractmethod
    def decorate_asyncgen[Y, S, **P](
        self,
        func: T.Callable[P, T.AsyncGenerator[Y, S]],
    ) -> T.Callable[P, T.AsyncGenerator[Y, S]]: ...

    # The order of overloads matters! First applicable one gets used.

    @T.overload
    @copy_signature_from(decorate_asyncgen)
    def __call__(self, func: T.Any) -> T.Any: ...

    @T.overload
    @copy_signature_from(decorate_gen)
    def __call__(self, func: T.Any) -> T.Any: ...

    @T.overload
    @copy_signature_from(decorate_async)
    def __call__(self, func: T.Any) -> T.Any: ...

    @T.overload
    @copy_signature_from(decorate_sync)
    def __call__(self, func: T.Any) -> T.Any: ...

    def __call__[R, **P](
        self,
        func: T.Callable[P, R],
    ) -> T.Callable[P, T.Any]:
        if inspect.isasyncgenfunction(func):
            return self.decorate_asyncgen(func)
        if inspect.iscoroutinefunction(func):
            return self.decorate_async(func)
        if inspect.isgeneratorfunction(func):
            return self.decorate_gen(func)

        return self.decorate_sync(func)


class UniversalDecoratorBase[*Context](UniversalDecorator):
    """Base class for custom `UniversalDecorator` implementations.

    Override the `_pre`, `_post`, `_except`, and `_finally` methods to customize
    the behavior. By default, they do nothing.
    """

    def _pre(
        self,
        args: list[T.Any],
        kwargs: dict[str, T.Any],
    ) -> tuple[*Context]:
        """Alter the arguments before they are passed to the decorated function.

        Args:
            args: Positional arguments for the decorated function.
            kwargs: Keyword arguments for the decorated function.

        Returns:
            Context which is passed as additional arguments to `_post`,
            `_except`, and `_finally`.

        Raises:
            StopIteration: Return a value immediately instead of calling the
                decorated function.
        """
        del args, kwargs
        return ()  # pyright: ignore[reportReturnType]

    def _post[R](self, result: R, *context: *Context) -> R:
        """Intercept the result returned by the decorated function.

        Args:
            result: Result returned by the decorated function.
            context: Context returned by `_pre`.

        Returns:
            Result to return to the caller.
        """
        del context
        return result

    def _except(self, exc: BaseException, *context: *Context) -> T.Any:
        """Handle an exception raised by the decorated function.

        Args:
            exc: Exception raised by the decorated function.
            context: Context returned by `_pre`.

        Returns:
            Result to return to the caller (and suppress the exception).

        Raises:
            BaseException: May be `exc` or a completely different exception.
        """
        del context
        raise exc

    def _finally(self, *context: *Context) -> None:
        """Clean up after the decorated function either returned or raised.

        The respective `_post` or `_except` method is called first, similar to
        a `finally` clause in a `try` statement.

        Args:
            context: Context returned by `_pre`.
        """
        del context

    @T.override
    def decorate_sync[R, **P](
        self,
        func: T.Callable[P, R],
    ) -> T.Callable[P, R]:
        @functools.wraps(func)
        def decorated(*args: P.args, **kwargs: P.kwargs) -> R:
            mutable_args = list(args)
            try:
                context = self._pre(mutable_args, kwargs)
            except StopIteration as e:
                return e.value

            try:
                result = func(*mutable_args, **kwargs)  # pyright: ignore[reportCallIssue]
            except BaseException as e:  # noqa: BLE001
                return self._except(e, *context)
            else:
                return self._post(result, *context)
            finally:
                self._finally(*context)

        return decorated

    @T.override
    def decorate_gen[Y, S, R, **P](
        self,
        func: T.Callable[P, T.Generator[Y, S, R]],
    ) -> T.Callable[P, T.Generator[Y, S, R]]:
        @functools.wraps(func)
        def decorated(
            *args: P.args, **kwargs: P.kwargs
        ) -> T.Generator[Y, S, R]:
            mutable_args = list(args)
            try:
                context = self._pre(mutable_args, kwargs)
            except StopIteration as e:
                return e.value

            try:
                result = yield from func(*mutable_args, **kwargs)  # pyright: ignore[reportCallIssue]
            except BaseException as e:  # noqa: BLE001
                return self._except(e, *context)
            else:
                return self._post(result, *context)
            finally:
                self._finally(*context)

        return decorated

    @T.override
    def decorate_async[R, **P](
        self,
        func: T.Callable[P, T.Awaitable[R]],
    ) -> T.Callable[P, T.Awaitable[R]]:
        @functools.wraps(func)
        async def decorated(*args: P.args, **kwargs: P.kwargs) -> R:
            mutable_args = list(args)
            try:
                context = self._pre(mutable_args, kwargs)
            except StopIteration as e:
                return e.value

            try:
                result = await func(*mutable_args, **kwargs)  # pyright: ignore[reportCallIssue]
            except BaseException as e:  # noqa: BLE001
                return self._except(e, *context)
            else:
                return self._post(result, *context)
            finally:
                self._finally(*context)

        return decorated

    @T.override
    def decorate_asyncgen[Y, S, **P](  # noqa: C901, PLR0915
        self,
        func: T.Callable[P, T.AsyncGenerator[Y, S]],
    ) -> T.Callable[P, T.AsyncGenerator[Y, S]]:
        @functools.wraps(func)
        async def decorated(  # noqa: C901, PLR0912, PLR0915
            *args: P.args, **kwargs: P.kwargs
        ) -> T.AsyncGenerator[Y, S]:
            mutable_args = list(args)
            try:
                context = self._pre(mutable_args, kwargs)
            except StopIteration as e:
                raise ReturnFromAsyncGenerator(e.value) from e

            try:
                # As of Python 3.13,`yield from` is not supported in async
                # functions.
                # See:
                #   https://peps.python.org/pep-0525/#asynchronous-yield-from
                #   https://discuss.python.org/t/yield-from-in-async-functions/47050
                #
                # The following code was taken from the `yield from` PEP and
                # adapted for async generators.
                # See:
                #   https://peps.python.org/pep-0380/#formal-semantics

                EXPR = func(*args, **kwargs)  # noqa: N806
                _i = EXPR
                try:
                    _y = await anext(_i)
                except StopAsyncIteration as _e:
                    _r = getattr(_e, "value", None)
                else:
                    while 1:
                        try:
                            _s = yield _y
                        except GeneratorExit as _e:
                            try:
                                _m = _i.aclose
                            except AttributeError:
                                pass
                            else:
                                await _m()
                            raise _e from None
                        except BaseException as _e:  # noqa: BLE001
                            _x = (type(_e), _e, _e.__traceback__)
                            try:
                                _m = _i.athrow
                            except AttributeError:
                                raise _e from None
                            else:
                                try:
                                    _y = await _m(*_x)
                                except StopAsyncIteration as _e:
                                    _r = getattr(_e, "value", None)
                                    break
                        else:
                            try:
                                if _s is None:
                                    _y = await anext(_i)
                                else:
                                    _y = await _i.asend(_s)
                            except StopAsyncIteration as _e:
                                _r = getattr(_e, "value", None)
                                break
                # There's no path where `_r` is unbound, right???
                RESULT = _r  # noqa: N806 # pyright: ignore[reportPossiblyUnboundVariable]

                # ============================================================ #

                result = RESULT

            except BaseException as e:  # noqa: BLE001
                self._except(e, *context)
            else:
                result = self._post(result, *context)
                if result is not None:
                    raise ReturnFromAsyncGenerator(result)
            finally:
                self._finally(*context)

        return decorated


class _UniversalDecoratorFromGeneratorFunction[Y, S, R, **P](
    UniversalDecoratorBase["T.Generator[Y, S, R]"],
):
    _genfunc: T.Callable[[list[T.Any], dict[str, T.Any]], T.Generator[Y, S, R]]

    def __init__(
        self,
        genfunc: T.Callable[
            [list[T.Any], dict[str, T.Any]],
            T.Generator[Y, S, R],
        ],
    ) -> None:
        self._genfunc = genfunc

    @T.override
    def _pre(
        self,
        args: list[T.Any],
        kwargs: dict[str, T.Any],
    ) -> tuple[T.Generator[Y, S, R]]:
        gen = self._genfunc(args, kwargs)
        try:
            _ = next(gen)
        except StopIteration as e:
            raise StopIteration(e.value) from None

        return (gen,)

    @T.override
    def _post(self, result: T.Any, gen: T.Generator[Y, S, R]) -> R:
        try:
            _ = gen.send(result)
        except StopIteration as e:
            return e.value

        errmsg = "generator didn't stop"
        raise RuntimeError(errmsg)

    @T.override
    def _except(self, exc: BaseException, gen: T.Generator[Y, S, R]) -> T.Any:
        try:
            _ = gen.throw(exc)
        except StopIteration as stop:
            # Make sure its not the exception we passed in.
            if stop is exc:
                raise stop from None
            return stop.value

        errmsg = "generator didn't stop"
        raise RuntimeError(errmsg)

    @T.override
    def _finally(self, gen: T.Generator[Y, S, R]) -> None:
        gen.close()


def universaldecorator[Y, S, R, **P](
    genfunc: T.Callable[[list[T.Any], dict[str, T.Any]], T.Generator[Y, S, R]],
) -> UniversalDecorator:
    """Create a `UniversalDecorator` from a generator function.

    ```
    @universaldecorator
    def decorator(args: list, kwargs: dict):
        # Modify args before they are passed to the decorated function.
        args.reverse()
        try:
            # Call the decorated function and get what it returned,
            # regardless of whether it is async and/or generator.
            result = yield
        except:
            # An exception was raised by the decorated function.
            return None  # suppress it
        else:
            return result
    ```
    """

    return _UniversalDecoratorFromGeneratorFunction(genfunc)
