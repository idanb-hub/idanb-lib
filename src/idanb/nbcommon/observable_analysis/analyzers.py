from __future__ import annotations

import textwrap
import typing

import polars as pl
import solara
from itables.widget import ITable

from analytics.connectors.intelowl.models import plugins
from idanb import components

from .component import analyzer_report_component

if typing.TYPE_CHECKING:
    import reacton
    import typing_extensions as T


ALL_ANALYZERS = [
    plugins.Classic_DNS,
    plugins.IPApi,
    plugins.Mnemonic_PassiveDNS,
    plugins.Robtex,
    plugins.TorProject,
    plugins.WhoIs_RipeDB_Search,
]


def DenseTableCSS() -> reacton.core.Element[T.Any]:  # noqa: N802
    return components.LocalCSS(
        rules={
            "td": textwrap.dedent("""\
                width: 50%;
                height: 2.4em;
                text-align: left;
            """),
        },
    )


@analyzer_report_component()
@solara.component
def IPApi(report: plugins.IPApi) -> None:  # noqa: N802
    with DenseTableCSS():
        solara.HTML("h2", "IP Info")
        # NOTE: I think there will always be just one ip_info item.
        for ip in report.report["ip_info"]:
            components.SimpleDictTable(ip)

        for key, dns in report.report["dns_info"].items():
            solara.HTML("h2", f"{key.upper()} Info")
            assert isinstance(dns, dict), "should be TypedDict"
            components.SimpleDictTable(dns)


@analyzer_report_component()
@solara.component
def Mnemonic_PassiveDNS(report: plugins.Mnemonic_PassiveDNS) -> None:  # noqa: N802
    df = pl.DataFrame(report.report)
    ITable.element(df=df)  # pyright: ignore[reportAttributeAccessIssue]


@analyzer_report_component()
@solara.component
def TorProject(report: plugins.TorProject) -> None:  # noqa: N802
    with DenseTableCSS():
        components.SimpleDictTable(report.report)


@analyzer_report_component()
@solara.component
def Classic_DNS(report: plugins.Classic_DNS) -> None:  # noqa: N802
    resolutions = pl.DataFrame(
        data=[
            {"domain": r} if isinstance(r, str) else r
            for r in report.report["resolutions"]
        ]
    )
    ITable.element(df=resolutions)  # pyright: ignore[reportAttributeAccessIssue]


@analyzer_report_component()
@solara.component
def Robtex(report: plugins.Robtex) -> None:  # noqa: N802
    dfs: dict[str, pl.DataFrame] = {}

    pdns_reports = [r for r in report.report if "status" not in r]
    dfs["Passive DNS"] = pl.DataFrame(pdns_reports)

    ip_report = next((r for r in report.report if "status" in r), None)
    if ip_report is not None:
        ip_report = dict(ip_report)
        del ip_report["status"]

        dfs["IP Query"] = pl.concat(
            pl.DataFrame(ip_report.pop(key), schema=["o", "t"])
            .rename({"o": "name", "t": "time"})
            .sort("time", descending=True)
            .with_columns(pl.lit(key).alias("source"))
            for key in ["act", "acth", "pas", "pash"]
        )

        with DenseTableCSS():
            components.SimpleDictTable(ip_report)

    with solara.Row(justify="space-evenly"):
        for title, df in dfs.items():
            with solara.Column(style="flex: 1;"):
                solara.HTML("h2", title)
                ITable.element(df=df)  # pyright: ignore[reportAttributeAccessIssue]


@analyzer_report_component()
@solara.component
def WhoIs_RipeDB_Search(report: plugins.WhoIs_RipeDB_Search) -> None:  # noqa: N802
    attributes: list[dict[str, object]] = []
    remarks: list[str] = []

    def append_remarks() -> None:
        attributes.append(
            {
                "name": "remarks",
                "value": "\n".join(remarks),
                "comment": "",
            }
        )
        remarks.clear()

    for obj in report.report["objects"]["object"]:
        attributes.clear()
        remarks.clear()

        for attribute in obj["attributes"]["attribute"]:
            if attribute["name"] == "remarks":
                remarks.append(attribute["value"])
                continue

            attribute.setdefault("comment", "")

            if remarks:
                append_remarks()

            attributes.append(dict(attribute))

        if remarks:
            append_remarks()

        solara.HTML("h2", f"{obj['link']['href']}")
        with DenseTableCSS():
            components.SimpleTable(attributes)
