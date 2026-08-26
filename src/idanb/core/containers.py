from __future__ import annotations

import dataclasses

import typing_extensions as T
import reacton
import yaml
from ipymui.components import mui

from idanb import infra, meta, react, ui, utils

if T.TYPE_CHECKING:
    pass


@utils.cache
def podman() -> infra.podman.Podman:
    return infra.podman.Podman()


_Tasks = react.create_global(
    dict[str, react.Task[[], infra.podman.Container]](),
    eq=False,
)


@dataclasses.dataclass()
class ContainerConfig:
    image: str


@utils.cache
def config() -> dict[str, ContainerConfig]:
    with meta.rootdir().joinpath("config/containers.yaml").open("r") as f:
        data = yaml.safe_load(f)

    if not utils.is_mapping(data, keys=str, values=dict):
        errmsg = "invalid containers config"
        raise RuntimeError(errmsg)

    return {name: ContainerConfig(**props) for name, props in data.items()}


def use_container(name: str) -> infra.podman.Container | None:
    tasks = _Tasks.peek()

    conf = config()[name]

    def set_task(task: react.Task[[], infra.podman.Container]) -> None:
        _Tasks.set(lambda tasks: {**tasks, name: task})

    @react.use_task()
    async def task() -> infra.podman.Container:
        return await podman().run(conf.image, data=meta.rootdir() / "data")

    try:
        task = tasks[name]
    except KeyError:
        task.start()

    set_task(task)

    match task.status:
        case task.Result(container):
            return container
        case _:
            return None


@reacton.component
def ContainersStatus() -> None:  # noqa: N802
    tasks, _ = react.use_global(_Tasks)

    if any(task.pending for task in tasks.values()):
        what = "container" if len(tasks) == 1 else f"{len(tasks)} containers"
        mui.Typography(f"Staring {what}...")
        mui.LinearProgress()

    failed_tasks: list[react.Task[[], T.Any]] = []

    for name, task in tasks.items():
        match task.status:
            case task.Exception(exception):
                ui.ExceptionAlert(
                    exception,
                    title=f"Container '{name}' failed to start.",
                )
            case task.Cancelled():
                mui.Alert(f"Container '{name}' not started.", severity="error")
            case _:
                continue

        failed_tasks.append(task)

    if failed_tasks:
        mui.Button(
            "Retry",
            onClick=lambda: utils.void([task.start() for task in failed_tasks]),
            variant="contained",
            fullWidth=True,
        )
