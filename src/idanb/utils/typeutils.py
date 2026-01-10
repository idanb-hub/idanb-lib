from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    import typing_extensions as T


class copy_signature_from[R, **P]:  # noqa: N801
    """Decorator to copy type annotations from another function/method."""

    @typing.overload
    def __init__[S](
        self,
        *,
        method: T.Callable[T.Concatenate[S, P], R],
    ) -> None:
        """Copy type annotations from another method.

        The first pamameter of method is omitted from the copied signature
        (meaning the `self` parameter is not copied).
        """

    @typing.overload
    def __init__(self, function: T.Callable[P, R]) -> None:
        """Copy type annotations from another function."""

    def __init__(self, function: T.Any = None, method: T.Any = None) -> None:
        """Copy type annotations from another function or method.

        If `method` is specified, its first pamameter is omitted from the copied
        signature (meaning the `self` parameter is not copied).
        """

    def __call__(self, function: T.Callable[..., T.Any]) -> T.Callable[P, R]:
        """Apply the copied signature onto a function."""
        return function

    def onto_method[S](
        self,
        method: T.Callable[T.Concatenate[S, ...], object],
    ) -> T.Callable[T.Concatenate[S, P], R]:
        """Apply the copied signature onto a method.

        The first parameter of the decorated method is added before the copied
        ones (meaning the `self` parameter is added).
        """
        return method  # pyright: ignore[reportReturnType]

    def keep_return[RKeep](
        self,
        function: T.Callable[..., RKeep],
    ) -> T.Callable[P, RKeep]:
        """Apply the copied signature, except the return type, onto a function.

        The return type of the decorated function is preserved.
        """
        return function
