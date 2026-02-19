from __future__ import annotations

import json
import typing

import pydantic
import reacton
import structlog
from ipymui import callback
from ipymui.components import mui

from analytics.connectors.intelowl.models import (
    PluginModel,
    PluginStatus,
)
from idanb import ui
from idanb.infra import intelowl

if typing.TYPE_CHECKING:
    import typing_extensions as T
    from reacton.core import Element


_logger = structlog.get_logger()


type AnalyzerReportCompoment = T.Callable[[T.Any], Element[T.Any]]


@typing.final
class analyzer_report_component:  # noqa: N801
    _components: T.ClassVar[dict[str, AnalyzerReportCompoment]] = {}

    def __init__(self, name: str | None = None) -> None:
        self.name = name

    def __call__[F: AnalyzerReportCompoment](self, f: F) -> F:
        name = self.name or f.__name__
        self._components[name] = f
        return f

    @classmethod
    def get(cls, name: str) -> AnalyzerReportCompoment | None:
        return cls._components.get(name)


def _job_progress(job: intelowl.models.Job) -> float:
    if not job.analyzer_reports:
        return 0

    finished_count = sum(
        PluginStatus(report["status"]).isfinal()
        for report in job.analyzer_reports
    )
    return finished_count / len(job.analyzer_reports) * 100


@reacton.component
def IntelOwl_ObservableAnalysis(  # noqa: N802
    *,
    analyzers: T.Sequence[str | type[PluginModel]],
) -> None:
    connector = reacton.use_memo(lambda: intelowl.IntelOwl())

    names = [
        analyzer if isinstance(analyzer, str) else analyzer.name
        for analyzer in analyzers
    ]
    models = {
        analyzer.name: analyzer
        for analyzer in analyzers
        if not isinstance(analyzer, str)
    }

    selected_names, set_selected_names = reacton.use_state(list(names))
    with mui.Stack(direction="column", gap=1):
        with mui.ToggleButtonGroup(
            value=selected_names,
            onChange=lambda _, value: set_selected_names(value),
            color="primary",
            sx=dict(
                flexWrap="wrap",
                gap="2px",
                **{
                    "& .MuiToggleButtonGroup-grouped": dict(
                        borderRadius="var(--mui-shape-borderRadius)",
                        borderCollapse="collapse",
                        border="1px solid var(--mui-palette-divider) !important",
                    ),
                },
            ),
        ):
            for name in names:
                mui.ToggleButton(name, value=name)

        observable, set_observable = reacton.use_state("")
        mui.TextField(
            defaultValue=observable,
            label="Observable",
            onBlur=callback("$[0].target.value")(set_observable),
            fullWidth=True,
        )

        submitted_names, set_submitted_names = reacton.use_state(list[str]())
        job, set_job = reacton.use_state(
            typing.cast("intelowl.models.Job | None", None),
        )

        @ui.use_task()
        async def query_task() -> None:
            set_job(None)

            # Order of values is not preserved in `selected_names`.
            set_submitted_names(sorted(selected_names, key=names.index))

            async with connector.observable_analysis(
                observable,
                analyzers_requested=selected_names,
            ) as query:
                while await query.poll():
                    set_job(query.job)
                set_job(query.job)

        mui.Button(
            ("Submit" if not query_task.pending else "Cancel"),
            onClick=lambda: (
                query_task() if not query_task.pending else query_task.cancel()
            ),
            disabled=not selected_names,
            color="primary" if not query_task.pending else "error",
            variant="contained",
            fullWidth=True,
            size="large",
        )

        if query_task.pending:
            progress = 0 if job is None else _job_progress(job)
            mui.LinearProgress(value=progress)

        if query_task.exception is not None:
            mui.Alert(str(query_task.exception), severity="error")
            return

        if job is None:
            return

        for error in job.errors:
            mui.Alert(error, severity="error")

        for warning in job.warnings:
            mui.Alert(warning, severity="warning")

    AnalyzerReports(
        models={name: models.get(name) for name in submitted_names},
        reports=job.analyzer_reports,
    )


@reacton.component
def AnalyzerReports(  # noqa: N802
    models: dict[str, type[intelowl.models.PluginModel] | None],
    reports: intelowl.models.PluginList,
) -> None:
    tab, set_tab = reacton.use_state(reports[0]["name"])

    with mui.Tabs(value=tab, onChange=lambda _, value: set_tab(value)):
        for name in models:
            mui.Tab(
                label=name,
                value=name,
                disabled=(reports.get(name) is None),
            )

    if tab is None:
        return

    for name, model in models.items():
        report = reports.get(name)

        with mui.Box(hidden=(name != tab)):
            if report is None:
                continue

            report = PluginModel.model_validate(report)
            if not report.status.isfinal():
                mui.CircularProgress()
                continue

            for error in report.errors:
                mui.Alert(error, severity="warning")

            component = analyzer_report_component.get(name)

            if model is not None:
                try:
                    report = model.model_validate(report)
                except pydantic.ValidationError:
                    mui.Alert(
                        "Response doesn't match expected format. "
                        "Showing raw report. ",
                        severity="error",
                    )
                    _logger.exception(
                        "Invalid analyzer report",
                        raw_report=report,
                    )
                    # Components expect valid data.
                    component = None

            if component is not None:
                component(report)
            else:
                mui.Typography(
                    json.dumps(report.get("report"), indent=2, default=str),
                    variant="body2",
                    sx=dict(
                        fontFamily="monospace",
                        whiteSpace="pre-wrap",
                    ),
                )
