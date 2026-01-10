from __future__ import annotations

import json
import typing

import pydantic
import reacton
import solara
import solara.lab
import structlog

from analytics.connectors.intelowl.models import (
    PluginModel,
    PluginStatus,
)
from idanb import components
from idanb.infrastructure import intelowl

if typing.TYPE_CHECKING:
    import typing_extensions as T


_logger = structlog.get_logger()


type AnalyzerReportCompoment = T.Callable[[T.Any], reacton.core.Element[T.Any]]


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


@solara.component
def IntelOwl_ObservableAnalysis(  # noqa: N802
    *,
    analyzers: T.Sequence[str | type[PluginModel]],
) -> None:
    connector = solara.use_memo(lambda: intelowl.IntelOwl())

    names = [
        analyzer if isinstance(analyzer, str) else analyzer.name
        for analyzer in analyzers
    ]
    models = {
        analyzer.name: analyzer
        for analyzer in analyzers
        if not isinstance(analyzer, str)
    }

    selected_names = solara.use_reactive(list(names))
    solara.ToggleButtonsMultiple(
        value=selected_names,
        values=names,
    )
    observable = solara.use_reactive("")
    solara.InputText(
        label="Observable",
        value=observable,
    )

    submitted_names: solara.Reactive[list[str]] = solara.use_reactive([])
    job: solara.Reactive[intelowl.models.Job | None] = solara.use_reactive(None)

    @solara.lab.use_task(dependencies=None, raise_error=False)
    async def query_task() -> None:
        job.set(None)

        # Order of values is not preserved in `selected_names`.
        submitted_names.set(sorted(selected_names.get(), key=names.index))

        async with connector.observable_analysis(
            observable.get(),
            analyzers_requested=selected_names.get(),
        ) as query:
            while await query.poll():
                job.set(query.job)
            job.set(query.job)

    components.TaskButton(
        task=query_task,
        label="Submit",
        disabled=not selected_names.get(),
        color="primary",
        if_pending={
            "label": "cancel",
            "color": "error",
            "disabled": False,
        },
    )

    if query_task.pending:
        progress = 0 if job.value is None else _job_progress(job.value)
    else:
        progress = False

    solara.ProgressLinear(progress)

    if query_task.not_called:
        return
    if query_task.cancelled:
        return
    if query_task.error:
        solara.Error(str(query_task.exception))
        return

    if job.value is None:
        return

    for error in job.value.errors:
        solara.Error(error)

    for warning in job.value.warnings:
        solara.Warning(warning)

    AnalyzerReports(
        models={name: models.get(name) for name in submitted_names.get()},
        reports=job.value.analyzer_reports,
    )


@solara.component
def AnalyzerReports(  # noqa: N802
    models: dict[str, type[intelowl.models.PluginModel] | None],
    reports: intelowl.models.PluginList,
) -> None:
    with solara.lab.Tabs(vertical=False):
        for name, model in models.items():
            report = reports.get(name)

            with solara.lab.Tab(name, disabled=report is None):
                if report is None:
                    continue

                report = PluginModel.model_validate(report)
                if not report.status.isfinal():
                    # TODO: Use custom spinner.
                    solara.SpinnerSolara()
                    continue

                for error in report.errors:
                    solara.Warning(error)

                component = analyzer_report_component.get(name)

                if model is not None:
                    try:
                        report = model.model_validate(report)
                    except pydantic.ValidationError:
                        solara.Error(
                            "Response doesn't match expected format. "
                            "Showing raw report. "
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
                    solara.Text(
                        json.dumps(report.get("report"), indent=2, default=str),
                        style={
                            "font-family": "monospace",
                            "white-space": "pre-wrap",
                        },
                    )
