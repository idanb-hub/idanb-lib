from __future__ import annotations

import csv
import dataclasses
import itertools
from pathlib import Path

import typing_extensions as T

from idanb import utils

from .ip_protocols import IP_PROTOCOLS, IPProtocol

# https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml
CSVPATH = Path(__file__).with_suffix(".csv")


@dataclasses.dataclass(frozen=True, slots=True)
class Port:
    number: int
    name: str
    description: str
    protocols: frozenset[IPProtocol]

    def __int__(self) -> int:
        return self.number

    @T.override
    def __str__(self) -> str:
        return self.name


def _parse_numbers(number: str) -> T.Iterable[int]:
    numbers = [int(n) for n in number.split("-")]

    match numbers:
        case [lo]:
            hi = lo
        case [lo, hi]:
            pass
        case _:
            return ()

    return range(lo, hi + 1)


def _load() -> T.Iterable[Port]:
    with CSVPATH.open(newline="", encoding="utf-8") as f:
        rows = csv.reader(f)
        _header = next(rows)

        ports: dict[int, Port] = {}

        for name, numbers, protocol, description, *_ in rows:
            if not name or not numbers or not protocol:
                continue
            for number in _parse_numbers(numbers):
                protocols = frozenset([IP_PROTOCOLS[protocol]])

                other = ports.get(number)
                if other is not None:
                    # This makes sense for most, but there are exceptions.
                    # For example: "biff", "comsat", "exec" share the same port.
                    ports[number] = dataclasses.replace(
                        other,
                        protocols=(protocols | other.protocols),
                    )
                else:
                    ports[number] = Port(
                        number=number,
                        name=name,
                        # Collapse long descriptions that span multiple lines.
                        description=description.replace("\n", " "),
                        protocols=protocols,
                    )

        return ports.values()


PORTS: T.Mapping[str | int, Port] = utils.dicts.CaselessDict(
    itertools.chain.from_iterable(
        ((port.name, port), (port.number, port)) for port in _load()
    )
)
