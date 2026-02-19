from __future__ import annotations

import functools
import os
import sys
import tomllib
import typing
import urllib.parse
from collections import defaultdict
from pathlib import Path

if typing.TYPE_CHECKING:
    import typing_extensions as T


# Because typeshed's annotation doesn't preserve docstrings.
if typing.TYPE_CHECKING:
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


@functools.cache
def nburl() -> tuple[str, dict[str, list[str]]]:
    """Get URL of the current notebook and its query parameters."""

    url = os.environ.get("VOILA_REQUEST_URL")
    if url is None:
        from idanb.infra.asset_server import asset_server  # noqa: PLC0415

        urlpath = nbpath().relative_to(rootdir()).as_posix()
        base = asset_server(rootdir())
        url = urllib.parse.urljoin(base, urlpath)
        return url, {}

    scheme, authority, path, query, _fragment = urllib.parse.urlsplit(url)
    url = urllib.parse.urlunsplit((scheme, authority, path, None, None))

    params: defaultdict[str, list[str]] = defaultdict(list)
    for name, value in urllib.parse.parse_qsl(query):
        params[name].append(value)

    return url, params


@functools.cache
def baseurl() -> str:
    """Get URL corresponding to this project's root directory."""

    url, _ = nburl()

    # Strip notebook path to get the base URL.
    path = nbpath().relative_to(rootdir()).as_posix()
    if not url.endswith(path):
        errmsg = f"current URL {url!r} does match notebook path {path!r}"
        raise RuntimeError(errmsg)
    return url.removesuffix(path)


def urlof(path: str | Path) -> str:
    """Get URL corresponding to `path`."""

    path = Path(path)

    base = baseurl()
    url = path.relative_to(rootdir()).as_posix()
    return urllib.parse.urljoin(base, url)
