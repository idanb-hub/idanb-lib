from __future__ import annotations

import textwrap
import typing

from idanb import utils

if typing.TYPE_CHECKING:
    import typing_extensions as T


_VIEWS: dict[str, dict[str, str]] = {}


def view(
    name: str,
    *,
    geoip: bool = False,
) -> str:
    """Get a predefined table view by its name.

    ```py
    f"SELECT {view("basic")} FROM ipfix"
    ```

    Args:
        name: Name of predefined view.
        geoip: Whether to add GeoIP columns.

    Raises:
        KeyError: No view named `name`.
    """
    columns = _VIEWS[name]

    if geoip:
        columns = utils.dicts.insert(columns, _GEOIP_COLUMNS)

    return ",\n".join(f'{expr} as "{name}"' for name, expr in columns.items())


def views() -> T.Collection[str]:
    """Get names of predefined table views."""
    return _VIEWS.keys()


_VIEWS["basic"] = {
    "START TIME - FIRST SEEN": "tslocal",
    "DURATION": "(iana__flowendmilliseconds - iana__flowstartmilliseconds) / 1000",
    "PROTOCOL": "iana__protocolidentifier",
    "SOURCE IP ADDRESS": "coalesce(iana__sourceipv4address, iana__sourceipv6address)",
    "SOURCE PORT": "iana__sourcetransportport",
    "DESTINATION IP ADDRESS": "coalesce(iana__destinationipv4address, iana__destinationipv6address)",
    "DESTINATION PORT": "iana__destinationtransportport",
    "TCP FLAGS": "iana__tcpcontrolbits__flags",
    "PACKETS": "iana__packetdeltacount",
    "BYTES": "iana__octetdeltacount",
}


_GEOIP_COLUMNS = {
    "SOURCE IP ADDRESS": {
        "SOURCE COUNTRY": "geoip_src.country_iso_code",
    },
    "DESTINATION IP ADDRESS": {
        "DESTINATION COUNTRY": "geoip_dst.country_iso_code",
    },
}


_VIEWS["extended"] = {
    **_VIEWS["basic"],
    "DETECTED PROTOCOL": "upper(proto__detected_type)",
    "HTTP HOST": "proto__http__host_http",
    "HTTP URL": "proto__http__url_http",
    "HTTP STATUS CODE": "proto__http__statuscode_http",
    "TLS SNI": "proto__tls__sni_tls",
    "DNS QNAME": "proto__dns__qname_dns",
    "DNS RESPONSE": "proto__dns__crrrdata_dns",
    "DNS RESPONSE TYPE": textwrap.dedent("""\
        CASE proto__dns__crrtype_dns
            WHEN 1  THEN 'A'
            WHEN 5  THEN 'CNAME'
            WHEN 28 THEN 'AAAA'
            WHEN 65 THEN 'HTTPS'
            WHEN 65535 THEN 'N/A'
            ELSE format('%s', proto__dns__crrtype_dns)
        END
    """),
}
