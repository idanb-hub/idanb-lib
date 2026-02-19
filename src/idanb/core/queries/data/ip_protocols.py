from __future__ import annotations

import csv
import dataclasses
import itertools
import typing
from pathlib import Path

from idanb import utils

if typing.TYPE_CHECKING:
    import typing_extensions as T


# https://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml
CSVPATH = Path(__file__).with_suffix(".csv")


@dataclasses.dataclass(frozen=True)
class IPProtocol:
    number: int
    name: str
    description: str

    def __int__(self) -> int:
        return self.number

    @typing.override
    def __str__(self) -> str:
        return self.name


def _load() -> T.Iterable[IPProtocol]:
    with CSVPATH.open(newline="", encoding="utf-8") as f:
        rows = csv.reader(f)
        _header = next(rows)

        for number, keyword, name, _, _ in rows:
            if not number.isnumeric() or not keyword:
                continue
            yield IPProtocol(
                number=int(number),
                name=keyword,
                # Long names are split across multiple lines.
                description=name.replace("\n", " "),
            )


IP_PROTOCOLS: T.Mapping[str | int, IPProtocol] = utils.dicts.CaselessDict(
    itertools.chain.from_iterable(
        ((proto.name, proto), (proto.number, proto)) for proto in _load()
    )
)
