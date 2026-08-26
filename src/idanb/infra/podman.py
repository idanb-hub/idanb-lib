from __future__ import annotations

import atexit
import contextlib
import json
import logging
import subprocess
from pathlib import Path

import typing_extensions as T

from idanb import utils

if T.TYPE_CHECKING:
    import types


_logger = logging.getLogger(__name__)


class Container(contextlib.AbstractAsyncContextManager["Container"]):
    id: str

    def __init__(self, id: str) -> None:
        self.id = id

    @T.overload
    def exec(
        self,
        args: T.Sequence[str],
        *,
        text: T.Literal[True],
        **kwargs: T.Unpack[utils.process.ProcessParams],
    ) -> utils.process.Process[str]: ...

    @T.overload
    def exec(
        self,
        args: T.Sequence[str],
        *,
        text: T.Literal[False] = False,
        **kwargs: T.Unpack[utils.process.ProcessParams],
    ) -> utils.process.Process[bytes]: ...

    def exec(
        self,
        args: T.Sequence[str],
        *,
        text: bool = False,
        **kwargs: T.Unpack[utils.process.ProcessParams],
    ) -> utils.process.Process[str] | utils.process.Process[bytes]:
        return utils.process.run(
            ["podman", "exec", self.id, *args],
            text=text,
            **kwargs,
        )

    async def stop(self, timeout: int = 1) -> None:  # noqa: ASYNC109
        _ = await utils.process.run(
            ["podman", "stop", f"--time={timeout}", self.id],
        )

    @T.override
    async def __aenter__(self) -> T.Self:
        return self

    @T.override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        try:
            await self.stop()
        except subprocess.CalledProcessError:
            _logger.exception("failed to stop container #%r", self.id)


type JSON = str | int | float | bool | None | list[JSON] | dict[str, JSON]


class Podman:
    def __init__(self) -> None:

        async def startup() -> None:
            try:
                info = await self.info()
            except subprocess.CalledProcessError as e:
                _logger.exception("Podman info failed: %r", e.stderr)
            else:
                _logger.debug("Podman info: %r", info)

        utils.forget_task(startup())

    async def info(self) -> JSON:
        stdout, _ = await utils.process.run(["podman", "info", "--format=json"])
        return json.loads(stdout)

    async def run(
        self,
        image: str,
        *,
        data: str | Path | None = None,
    ) -> Container:
        args = [
            "--detach",
            "--rm",
        ]

        if data is not None:
            data = Path(data)
            data.mkdir(parents=True, exist_ok=True)
            args.append(f"--volume={data}:/data")

        stdout, _ = await utils.process.run(
            ["podman", "run", *args, image],
            text=True,
        )

        container_id = stdout.strip()
        _logger.info("Container #%s started from image %s", container_id, image)

        atexit.register(
            lambda: utils.process.run(
                ["podman", "stop", "--time=1", container_id],
            ).wait(),
        )
        return Container(container_id)
