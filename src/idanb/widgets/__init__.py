"""Interactive widgets for asynchronous notebooks.

This module is a drop-in replacement for `ipywidgets`.
Some APIs are extended, but backwards compatibility is preserved.
"""

from ipywidgets import *  # noqa: F403

from .custom.clipboard import CopyToClipboard as CopyToClipboard
from .custom.logs import Logs as Logs
from .custom.perspective import PerspectiveWidget as PerspectiveWidget

# These override names imported from ipywidgets.
from .patched.button import Button as Button
from .patched.output import Output as Output
