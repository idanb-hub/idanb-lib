"""Global configuration.

```py
from idanb.core.config import CONFIG

@CONFIG.register("foo")
@dataclasses.dataclass()
class FooConfig:
    bar: str      # required
    baz: int = 1  # optional

# Then anywhere else ...
fooconf = CONFIG[FooConfig]
print(fooconf.bar)
```
"""

from __future__ import annotations

import collections.abc
import typing
from pathlib import Path

import yaml

if typing.TYPE_CHECKING:
    import typing_extensions as T


class ConfigError(ValueError):
    message: str
    path: tuple[str | int, ...]

    def __init__(
        self,
        message: str,
        path: tuple[str | int, ...],
        *args: object,
    ) -> None:
        super().__init__(message, path, *args)
        self.message = message
        self.path = path

    @typing.override
    def __str__(self) -> str:
        path = (
            "".join(
                f".{key}" if isinstance(key, str) else f"[{key!r}]"
                for key in self.path
            )
            or "<ROOT>"
        )
        return f"{self.message} at {path}"


class Config:
    """Configuration manager that tracks and creates configuration classes.

    Allows modules to register their configuration classes. Once the managed
    configuration is set, acts as a mapping from registered types to their
    configured instances.
    """

    _data: object
    _prefixes: dict[type, tuple[str | int, ...]]
    _cache: dict[type, object]

    def __init__(self) -> None:
        self._data = None
        self._prefixes = {}
        self._cache = {}

    def configure(self, data: object) -> None:
        """Set the managed configuration.

        For example, data loaded with `json.load`.
        """
        self._data = data
        self._cache.clear()

    @typing.overload
    def __getitem__(self, path: str | int | tuple[str | int, ...]) -> object:
        """Return a value from the managed configuration.

        Raises:
            ConfigError: No such value exists.
        """

    @typing.overload
    def __getitem__[Cls](self, cls: type[Cls]) -> Cls:
        """Return a class instance created from the managed configuration.

        The class type must have been previously registered with `register`.

        Raises:
            ConfigError: Configuration is invalid.
            TypeError: Requested class has not been previously registered.
        """

    @typing.no_type_check
    def __getitem__(self, cls_or_path):
        if isinstance(cls_or_path, type):
            return self._getinstance(cls_or_path)
        if isinstance(cls_or_path, tuple):
            return self._getvalue(*cls_or_path)
        return self._getvalue(cls_or_path)

    def get[Default](
        self,
        *path: str | int,
        default: Default = None,
    ) -> object | Default:
        """Return a value from the managed configuration if it exists.

        Args:
            path: Path to the desired value.
            default: Value to return if `path` does not exist.
        """
        try:
            return self._getvalue(*path)
        except ConfigError:
            return default

    def _getvalue(self, *path: str | int) -> object:
        value = self._data
        for i, key in enumerate(path, start=0):
            # Ensure current value is indexable.
            if isinstance(value, collections.abc.Mapping):
                pass
            elif not isinstance(value, collections.abc.Sequence):
                errmsg = f"expected list or map, found {type(value).__name__}"
                raise ConfigError(errmsg, path[:i])
            elif not isinstance(key, int):
                errmsg = "expected map, found list"
                raise ConfigError(errmsg, path[:i])

            try:
                value = value[typing.cast("T.Any", key)]
            except LookupError as e:
                errmsg = "missing value"
                raise ConfigError(errmsg, path[: i + 1]) from e

        return value

    def _getinstance[Cls](self, cls: type[Cls]) -> Cls:
        cached = self._cache.get(cls)
        if cached is not None:
            return typing.cast("Cls", cached)

        prefix = self._prefixes.get(cls)
        if prefix is None:
            errmsg = f"type {cls.__qualname__} is not stored in this config"
            raise TypeError(errmsg)

        config = self._getvalue(*prefix)
        if not isinstance(config, collections.abc.Mapping):
            errmsg = f"expected map, found {type(config).__name__!r}"
            raise ConfigError(errmsg, prefix)
        try:
            instance = cls(**config)
        except (AssertionError, TypeError, ValueError) as e:
            errmsg = f"invalid config for {cls.__name__!r}"
            raise ConfigError(errmsg, prefix) from e

        self._cache[cls] = instance
        return instance

    def register[Cls](
        self,
        *prefix: str | int,
    ) -> T.Callable[[type[Cls]], type[Cls]]:
        """Create a decorator for registering configuration classes.

        Args:
            prefix: Path to the class' data within the managed configuration.

        Returns:
            Decorator that registers the class it is applied on.

        The registered class gets constructed with `cls(**self[*prefix])`.
        """

        def decorator(cls: type[Cls]) -> type[Cls]:
            self._prefixes[cls] = prefix
            return cls

        return decorator


def find_config(filename: str | Path, start: str | Path = ".") -> Path:
    """Find `filename` in `start` or one of its parent directories.

    Raises:
        FileNotFoundError: Search stopped at either filesystem or project root
            (directory containing `pyproject.toml`).
    """
    directories: list[Path] = []
    reason = "stopped at filesystem root"

    for parent in Path(start).absolute().parents:
        path = parent.joinpath(filename)
        if path.is_file():
            return path
        directories.append(parent)
        if parent.joinpath("pyproject.toml").is_file():
            reason = "stopped at project root (found pyproject.toml)"
            break

    exc = FileNotFoundError(f"configuration file {str(filename)!r} not found")
    exc.add_note("the following directories were searched:")
    for directory in directories:
        exc.add_note(f"  {directory}")
    exc.add_note(reason)
    raise exc


DEFAULT_CONFIG = "config.yaml"

# Expose a single global config instance.
CONFIG: Config


def configure(file: str | Path = DEFAULT_CONFIG) -> Config:
    """Load the global configuration from a specified YAML file.

    If `file` contains a directory separator, it is resolved relative to CWD.
    Otherwise, `find_config()` is used to find the file in CWD or its parents.
    Once found, the file is loaded and its contents set as the global
    configuration (`CONFIG`), which is also returned.
    """

    file = Path(file)
    file = find_config(file) if file.name == str(file) else file.absolute()

    with file.open("r") as stream:
        data: object = yaml.safe_load(stream)

    config = Config()
    config.configure(data)
    globals()["CONFIG"] = config
    return config


# Automatically create and load CONFIG when it gets first accessed.
def __getattr__(name: str) -> T.Any:
    if name == "CONFIG":
        return configure(DEFAULT_CONFIG)
    raise AttributeError
