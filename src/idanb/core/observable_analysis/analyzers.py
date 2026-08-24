from __future__ import annotations

import typing_extensions as T
import polars as pl
from ipymui.components import mui
from itables.widget import ITable

from analytics.connectors.intelowl.models import plugins
from idanb import react, ui

from .component import analyzer_report_component

ALL_ANALYZERS = [
    plugins.Classic_DNS,
    plugins.IPApi,
    plugins.Mnemonic_PassiveDNS,
    plugins.Robtex,
    plugins.TorProject,
    plugins.WhoIs_RipeDB_Search,
]


@analyzer_report_component()
@react.component
def IPApi(report: plugins.IPApi) -> None:  # noqa: N802
    with mui.Box():
        mui.Typography("IP Info", variant="h5")
        # NOTE: I think there will always be just one ip_info item.
        for ip in report.report["ip_info"]:
            ui.SimpleDictTable(ip)

        for key, dns in report.report["dns_info"].items():
            mui.Typography(f"{key.upper()} Info", variant="h5")
            assert isinstance(dns, dict), "should be TypedDict"
            ui.SimpleDictTable(dns)


@analyzer_report_component()
@react.component
def Mnemonic_PassiveDNS(  # noqa: N802
    report: plugins.Mnemonic_PassiveDNS,
) -> react.Element[T.Any]:
    df = pl.DataFrame(report.report)
    return ITable.element(df=df)


@analyzer_report_component()
@react.component
def TorProject(report: plugins.TorProject) -> None:  # noqa: N802
    ui.SimpleDictTable(report.report)


@analyzer_report_component()
@react.component
def Classic_DNS(report: plugins.Classic_DNS) -> None:  # noqa: N802
    resolutions = pl.DataFrame(
        data=[
            {"domain": r} if isinstance(r, str) else r
            for r in report.report["resolutions"]
        ]
    )
    ITable.element(df=resolutions)


@analyzer_report_component()
@react.component
def Robtex(report: plugins.Robtex) -> None:  # noqa: N802
    dfs: dict[str, pl.DataFrame] = {}

    pdns_reports = [r for r in report.report if "status" not in r]
    dfs["Passive DNS"] = pl.DataFrame(pdns_reports)

    with mui.Box():
        ip_report = next((r for r in report.report if "status" in r), None)
        if ip_report is not None:
            ip_report = dict(ip_report)
            del ip_report["status"]

            dfs["IP Query"] = pl.concat(
                pl.DataFrame(ip_report.pop(key), schema=["o", "t"])
                .rename({"o": "name", "t": "time"})
                .sort("time", descending=True)
                .with_columns(pl.lit(key).alias("source"))
                for key in ["act", "acth", "pas", "pash"]  # codespell:ignore
            )

            ui.SimpleDictTable(ip_report)

        with mui.Stack(direction="row", justify="space-evenly"):
            for title, df in dfs.items():
                with mui.Stack(direction="column", flex=1):
                    mui.Typography(title, variant="h5")
                    ITable.element(df=df)


@analyzer_report_component()
@react.component
def WhoIs_RipeDB_Search(  # noqa: N802
    report: plugins.WhoIs_RipeDB_Search,
) -> None:
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

    with mui.Box():
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

            mui.Typography(f"{obj['link']['href']}", variant="h5")
            ui.SimpleTable(attributes)
