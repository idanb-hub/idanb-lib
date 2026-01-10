from __future__ import annotations

import collections
import typing

if typing.TYPE_CHECKING:
    import typing_extensions as T


class TransformDict[K, V](collections.UserDict[K, V]):
    """Dictionary that transforms keys using a provided function."""

    transform: T.Callable[[K], K]

    def __init__(
        self,
        transform: T.Callable[[K], K],
        init: T.Iterable[tuple[K, V]] | T.Mapping[K, V] = (),
        /,
        **kwargs: V,
    ) -> None:
        self.transform = transform
        super().__init__(init, **kwargs)

    @typing.override
    def __getitem__(self, key: K) -> V:
        return super().__getitem__(self.transform(key))

    @typing.override
    def __setitem__(self, key: K, item: V) -> None:
        return super().__setitem__(self.transform(key), item)

    @typing.override
    def __delitem__(self, key: K) -> None:
        return super().__delitem__(self.transform(key))

    @typing.override
    def __contains__(self, key: object) -> bool:
        try:
            transformed = self.transform(key)  # pyright: ignore[reportArgumentType]
        except TypeError:
            return False
        return super().__contains__(transformed)


class CaselessDict[K, V](TransformDict[K, V]):
    """Case insensitive dictionary. Keys are stored in lowercase."""

    def __init__(
        self,
        init: T.Iterable[tuple[K, V]] | T.Mapping[K, V] = (),
        /,
        **kwargs: V,
    ) -> None:
        def transform(key: K) -> K:
            if isinstance(key, str | bytes):
                return typing.cast("K", key.lower())
            return key

        super().__init__(transform, init, **kwargs)


def insert[K, V](
    mapping: T.Mapping[K, V],
    inserts: T.Mapping[K, T.Mapping[K, V]],
) -> dict[K, V]:
    """Create dictionary with additional items inserted after specific keys.

    >>> insert({1: 1, 3: 3}, {1: {2: 2}})
    {1: 1, 2: 2, 3: 3}
    """
    d: dict[K, V] = {}
    for k, v in mapping.items():
        d[k] = v
        insert = inserts.get(k, None)
        if insert is not None:
            d.update(insert)
    return d
