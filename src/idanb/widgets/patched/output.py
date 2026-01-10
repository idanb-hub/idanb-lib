from __future__ import annotations

import contextlib
import contextvars
import sys
import typing
import warnings

import ipywidgets
from ipykernel.zmqshell import ZMQDisplayPublisher
from IPython.core import ultratb
from IPython.core.getipython import get_ipython

from idanb import utils
from idanb.utils.asynctools import ContextProxy

if typing.TYPE_CHECKING:
    import types

    import typing_extensions as T


_ACTIVE_OUTPUT = contextvars.ContextVar["Output"]("_ACTIVE_OUTPUT")


# https://ipykernel.readthedocs.io/en/stable/api/ipykernel.html#ipykernel.zmqshell.ZMQDisplayPublisher.register_hook
def _display_hook(msg: dict[str, T.Any]) -> dict[str, T.Any] | None:
    output = _ACTIVE_OUTPUT.get(None)
    if output is None:
        return msg

    if msg["msg_type"] != "display_data":
        return msg

    # Instead of sending the message to the frontend, append it to the active
    # output directly (normally, this is done at the frontend).

    output.append_raw(
        {
            "output_type": "display_data",
            "data": msg["content"]["data"],
            "metadata": msg["content"]["metadata"],
        }
    )

    return None  # means don't send the message


def hook_outputs() -> None:
    """Prepare the interpreter for the patched `Output` widget.

    Hooks `sys.stdin`, `sys.stdout`, and IPython's `display` channel.
    """
    ip = get_ipython()
    if ip is None or not isinstance(ip.display_pub, ZMQDisplayPublisher):
        msg = "could not hook 'display'"
        warnings.warn(msg, stacklevel=2)
    else:
        ip.display_pub.unregister_hook(_display_hook)
        ip.display_pub.register_hook(_display_hook)

    if not isinstance(sys.stdout, ContextProxy):
        sys.stdout = ContextProxy(sys.stdout)

    if not isinstance(sys.stderr, ContextProxy):
        sys.stderr = ContextProxy(sys.stderr)


def _is_hooked[Obj](obj: Obj, name: str) -> T.TypeGuard[ContextProxy[Obj]]:
    if isinstance(obj, ContextProxy):
        return True

    msg = f"{name} hook is no longer installed, cannot capture output"
    warnings.warn(msg, stacklevel=2)
    return False


class Output(ipywidgets.Output):
    tbprinter: ultratb.TBTools

    if typing.TYPE_CHECKING:
        # It's a traitlet, but pyright handles this better ...
        outputs: tuple[dict[str, T.Any], ...] | list[dict[str, T.Any]]

    __tokens: list[
        tuple[
            contextvars.Token[Output],
            contextvars.Token[T.TextIO] | None,
            contextvars.Token[T.TextIO] | None,
        ],
    ]

    def __init__(
        self,
        /,
        tbprinter: ultratb.TBTools | None = None,
        **kwargs: T.Any,
    ) -> None:
        hook_outputs()
        super().__init__(**kwargs)

        if tbprinter is None:
            tbprinter = ultratb.FormattedTB(mode="Verbose", tb_offset=0)
            # Pyright seems to think it can be `None`.
            assert tbprinter is not None, "impossible"
        self.tbprinter = tbprinter

        self.__tokens = []
        self.__stdout = utils.iotools.TextIOAdapter(write=self.append_stdout)
        self.__stderr = utils.iotools.TextIOAdapter(write=self.append_stderr)

    @typing.override
    def __enter__(self) -> None:  # pyright: ignore[reportMissingSuperCall]
        self._flush()

        output = _ACTIVE_OUTPUT.set(self)
        stdout = (
            ContextProxy.set(sys.stdout, self.__stdout)
            if _is_hooked(sys.stdout, "stdout")
            else None
        )
        stderr = (
            ContextProxy.set(sys.stderr, self.__stderr)
            if _is_hooked(sys.stderr, "stderr")
            else None
        )
        self.__tokens.append((output, stdout, stderr))

    @typing.override
    def __exit__(  # pyright: ignore[reportMissingSuperCall]
        self,
        etype: type[BaseException] | None,
        evalue: BaseException | None,
        tb: types.TracebackType | None,
    ) -> T.Literal[True] | None:
        if etype is not None:
            lines = self.tbprinter.structured_traceback(etype, evalue, tb)
            sys.stderr.write("\n".join(lines))

        self._flush()
        output, stdout, stderr = self.__tokens.pop()

        _ACTIVE_OUTPUT.reset(output)

        if stdout is not None and _is_hooked(sys.stdout, "stdout"):
            ContextProxy.reset(sys.stdout, stdout)

        if stderr is not None and _is_hooked(sys.stderr, "stderr"):
            ContextProxy.reset(sys.stderr, stderr)

        # NOTE: Not suppressing the error results in it being printed out twice.
        return None

    @typing.override
    def clear_output(
        self,
        wait: bool = False,
        *args: T.Any,
        **kwargs: T.Any,
    ) -> None:
        if wait:

            def on_change(change: T.Any) -> None:
                with contextlib.suppress(ValueError):
                    # Apparently, this can fail sometimes. Not sure why.
                    self.unobserve(on_change, "outputs")
                # Remove old outputs.
                self.outputs = change.new[len(change.old) :]

            self.observe(on_change, "outputs")
        else:
            self.outputs = ()

    @typing.override
    def capture(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        clear_output: bool = False,
        *clear_args: T.Any,
        **clear_kwargs: T.Any,
    ) -> utils.decorator.UniversalDecorator:
        @utils.decorator.universaldecorator
        def decorator(_args: object, _kwargs: object) -> T.Generator[object]:
            if clear_output:
                self.clear_output(*clear_args, **clear_kwargs)
            with self:
                return (yield)

        return decorator

    @typing.override
    def append_display_data(self, display_object: object) -> None:
        if isinstance(display_object, ipywidgets.Widget):
            self._register_displayed_widget(display_object)
        super().append_display_data(display_object)

    def _register_displayed_widget(self, widget: ipywidgets.Widget) -> None:
        """Hook `widget.close` to remove `widget` from `self.outputs`."""  # noqa: D401
        # At the frontend, when a widget model closes, it is automatically
        # removed from all outputs. But if outputs are modified while that is
        # happening, the removal doesn't go though.
        close = widget.close
        model_id = widget.model_id

        def hook(*args: T.Any, **kwargs: T.Any) -> T.Any:
            self.outputs = [
                output
                for output in self.outputs
                if _get_model_id(output) != model_id
            ]
            close(*args, **kwargs)

        widget.close = hook

    def append_raw(self, *outputs: dict[str, T.Any]) -> None:
        """Append output messages directly."""
        for output in outputs:
            model_id = _get_model_id(output)
            if model_id is None:
                continue
            # Hook widgets displayed in the appended outputs.
            widget = ipywidgets.Widget.widgets[model_id]
            self._register_displayed_widget(widget)

        self.outputs += outputs


def _get_model_id(msg: dict[str, T.Any]) -> str | None:
    """If `msg` displays a widget, return its model ID, else return None."""
    if msg["output_type"] != "display_data":
        return None
    view = msg["data"].get("application/vnd.jupyter.widget-view+json")
    if view is None:
        return None
    return view["model_id"]
