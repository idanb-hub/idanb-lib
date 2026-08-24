from __future__ import annotations

import functools
import os
import sys
import tomllib
import urllib.parse
from pathlib import Path

import typing_extensions as T

# Because typeshed's annotation doesn't preserve docstrings.
if T.TYPE_CHECKING:
    functools.cache = lambda f: f


@functools.cache
def rootdir() -> Path:
    """Get the absolute path of this project's root directory."""
    for parent in nbpath().parents:
        path = parent / "pyproject.toml"
        if not path.is_file():
            continue

        with path.open("rb") as f:
            pyproject = tomllib.load(f)

        project: dict[str, T.Any] | None = pyproject.get("project")
        if not isinstance(project, dict):
            continue

        name = project.get("name")
        if name == "idanb-lib":
            continue

        return parent

    errmsg = "can't determine project root directory path"
    raise RuntimeError(errmsg)


def datadir() -> Path:
    """Get the absolute path of this project's data directory.

    The directory is created if it doesn't exist already.
    """
    path = rootdir() / "data"
    if not path.is_dir():
        path.mkdir(parents=True)

    return path


def cachedir() -> Path:
    """Get the absolute path of this project's cache directory.

    The directory is created if it doesn't exist already.
    """
    path = datadir() / ".cache"
    if not path.is_dir():
        path.mkdir(parents=True)

    return path


@functools.cache
def nbpath() -> Path:
    """Get the absolute path of the current notebook."""
    # This is the notebook's module.
    main = sys.modules["__main__"]

    # Voila exposes its request URL as an environment variable.
    url = os.environ.get("VOILA_REQUEST_URL")
    if url is not None:
        # Combine filename from the URL and CWD to get the notebook path.
        urlpath = urllib.parse.urlsplit(url).path
        return Path.cwd() / Path(urlpath).name

    # Otherwise, these variables might contain the notebook path.
    for var in [
        "__session__",  # JupyterLab
        "__vsc_ipynb_file__",  # VS Code
    ]:
        path: object = vars(main).get(var)
        if path is None:
            continue
        if not isinstance(path, str):
            errmsg = f"{var!r} should be 'str', not {type(path).__qualname__!r}"
            raise TypeError(errmsg)
        return Path(path)

    for var in [
        "JPY_SESSION_NAME",
    ]:
        path = os.environ.get(var)
        if path is not None:
            return Path(path)

    errmsg = "can't determine notebook path"
    raise RuntimeError(errmsg)
