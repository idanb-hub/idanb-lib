from __future__ import annotations

import functools
import typing

if typing.TYPE_CHECKING:
    import typing_extensions as T


def then[ROuter, RInner, **PInner, **POuter](
    outer: T.Callable[T.Concatenate[RInner, POuter], ROuter],
    /,
    *args: POuter.args,
    **kwargs: POuter.kwargs,
) -> T.Callable[[T.Callable[PInner, RInner]], T.Callable[PInner, ROuter]]:
    """Create a decorator that wraps a function in another.

    Additional arguments are forwarded to the wrapping function.

    >>> @then(dict, y="y")
    ... def example():
    ...     yield "x", "x"
    >>> example()
    {'x': 'x', 'y': 'y'}
    """

    def decorator(
        inner: T.Callable[PInner, RInner],
    ) -> T.Callable[PInner, ROuter]:
        @functools.wraps(inner)
        def decorated(
            *inner_args: PInner.args,
            **inner_kwargs: PInner.kwargs,
        ) -> ROuter:
            result = inner(*inner_args, **inner_kwargs)
            return outer(result, *args, **kwargs)

        return decorated

    return decorator
