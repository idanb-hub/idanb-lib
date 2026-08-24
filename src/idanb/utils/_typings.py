from __future__ import annotations

from collections.abc import Mapping, Sequence

import typing_extensions as T


def is_mapping[Key, Value](
    obj: object,
    *,
    keys: type[Key] = object,
    values: type[Value] = object,
) -> T.TypeIs[Mapping[Key, Value]]:
    """Return whether `obj` is `Mapping` from `keys` to `values`.

    >>> is_mapping({1: 1, 2: 2}, keys=int, values=int)
    True
    >>> is_mapping({1: 1, 2: "2"}, keys=int, values=int)
    False
    >>> is_mapping({1: 1, 2: "2"}, keys=int)
    True
    >>> is_mapping({}, keys=str, values=bool)
    True

    """
    if not isinstance(obj, Mapping):
        return False

    # Otherwise Pyright complains about unknown variables.
    obj = T.cast("Mapping[T.Any, object]", obj)

    # Don't check contents if we don't have to.
    if keys is object and values is object:
        return True

    return all(
        isinstance(key, keys) and isinstance(value, values)
        for key, value in obj.items()
    )


def is_sequence[Elem](
    obj: object,
    /,
    *,
    elems: type[Elem] = object,
) -> T.TypeIs[Sequence[Elem]]:
    """Return whether `obj` is a `Sequence` of `elems`.

    >>> is_sequence([1, 2], elems=int)
    True
    >>> is_sequence([1, "2"], elems=int)
    False
    >>> is_sequence([1, "2"])
    True
    >>> is_sequence([], elems=str)
    True

    """
    if not isinstance(obj, Sequence):
        return False

    # Don't check contents if we don't have to.
    if elems is object:
        return True

    return all(isinstance(elem, elems) for elem in obj)
