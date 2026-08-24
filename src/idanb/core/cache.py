from __future__ import annotations

import contextlib
import hashlib
import inspect
import logging
import os
import pickle

import typing_extensions as T

from idanb import meta, utils

_logger = logging.getLogger(__name__)


def _cache_key(
    func: T.Callable[..., object],
    *args: object,
    **kwargs: object,
) -> str:
    # Normalize positional/keyword arguments against function signature.
    signature = inspect.signature(func)
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    # Include function "path" in key.
    key = (func.__module__, func.__qualname__, bound.arguments)
    return hashlib.sha256(pickle.dumps(key)).hexdigest()


def _cache_load(key: str) -> T.Any:
    path = meta.cachedir() / key

    if not path.is_file():
        raise KeyError

    # Update timestamps.
    with contextlib.suppress(OSError):
        os.utime(path)

    _logger.info("Returning cached result")
    with path.open("rb") as f:
        return pickle.load(f)  # noqa: S301


def _cache_store(key: str, obj: object) -> None:
    path = meta.cachedir() / key

    with path.open("wb") as f:
        return pickle.dump(obj, f)


def fs_cache[**Params, Result]() -> T.Callable[
    [T.Callable[Params, Result]],
    T.Callable[Params, Result],
]:
    """Persistent function cache.

    Requires both function arguments and the cached results to be pickle-able.

    ```py
    @fs_cache()
    def cache_xy(x, y):
        return x + y
    ```

    Use closures to exclude arguments from being cached.

    ```py
    def cache_x(x, y):
        @fs_cache()
        def impl(x):
            return x + y
        return impl(x)
    ```
    """  # noqa: D401

    def decorator(
        func: T.Callable[Params, Result],
    ) -> T.Callable[Params, Result]:

        @utils.decorator.universaldecorator
        def impl(
            args: list[object],
            kwargs: dict[str, object],
        ) -> T.Generator[None, Result, Result]:
            key = _cache_key(func, *args, **kwargs)

            try:
                return _cache_load(key)
            except KeyError:
                pass
            except OSError:
                _logger.exception("Error loading %r from cache", key)

            result = yield
            _cache_store(key, result)
            return result

        return impl(func)

    return decorator
