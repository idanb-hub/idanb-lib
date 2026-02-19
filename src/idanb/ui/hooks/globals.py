from __future__ import annotations

import uuid

import reacton
import typing_extensions as T


class StateParams[Value](T.TypedDict, total=False):
    key: str
    eq: T.Callable[[Value, Value], bool]


class Global[Value]:
    _value: Value
    _setters: dict[
        uuid.UUID,
        T.Callable[[Value | T.Callable[[Value], Value]], None],
    ]
    _kwargs: StateParams[Value]

    def __init__(
        self,
        value: Value,
        **kwargs: T.Unpack[StateParams[Value]],
    ) -> None:
        self._value = value
        self._setters = {}
        self._kwargs = kwargs

    def peek(self) -> Value:
        return self._value

    def set(self, value: Value | T.Callable[[Value], Value]) -> None:
        # Ensure updater function runs only once.
        if callable(value):
            value = value(self._value)
        self._value = value
        for setter in self._setters.values():
            setter(lambda _: value)

    def use(self) -> Value:
        value, set_value = reacton.use_state(self._value, **self._kwargs)
        key = reacton.use_memo(lambda: uuid.uuid4())
        self._setters[key] = set_value
        return value


def create_global[Value](
    value: Value,
    **kwargs: T.Unpack[StateParams[Value]],
) -> Global[Value]:
    return Global(value, **kwargs)


def use_global[Value](
    global_: Global[Value], /
) -> tuple[Value, T.Callable[[Value | T.Callable[[Value], Value]], None]]:
    return global_.use(), global_.set
