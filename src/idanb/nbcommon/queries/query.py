from __future__ import annotations

import itertools
import string
import typing

if typing.TYPE_CHECKING:
    import typing_extensions as T


SQL_FMTSPEC: T.Final = "SQL"


class _QueryFormatter(string.Formatter):
    _on_param: T.Callable[[T.Any], None]

    def __init__(
        self,
        on_param: T.Callable[[T.Any], None] = lambda _: None,
    ) -> None:
        self._on_param = on_param
        super().__init__()

    @typing.override
    def vformat(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        format_string: str,
        args: T.Sequence[object],
        kwargs: T.Mapping[str, object],
    ) -> str:
        return super().vformat(format_string, args, kwargs)

    @typing.override
    def format_field(
        self,
        value: object,
        format_spec: str,
    ) -> object:
        if isinstance(value, Query):
            for param in value.params:
                self._on_param(param)
            return value.query

        if format_spec.endswith(SQL_FMTSPEC):
            format_spec = format_spec.removesuffix(SQL_FMTSPEC)
            return value

        if self._on_param is not None:
            self._on_param(value)
        return "?"


class Query:
    """Parameterized SQL query.

    Parameters use Python's `format` placeholder syntax.

    >>> q = Query("SELECT {x}", x=1)
    >>> q.query
    'SELECT ?'
    >>> q.params
    ('1',)

    To insert raw SQL, use the custom `:SQL` format specifier.

    >>> q = Query("SELECT {x:SQL}", x="NULL")
    >>> q.query
    'SELECT NULL'

    Subqueries are always inserted as raw SQL.
    Their parameters become parameters of the query.

    >>> q = Query("{} + {}", 1, Query("{} - {}", 2, 3))
    >>> q.query
    '? + ? - ?'
    >>> q.params
    ('1', '2', '3')
    """

    # https://peps.python.org/pep-0622/#special-attribute-match-args
    __match_args__: T.Final = ("query", "params")

    _query: str
    _params: tuple[object, ...]

    def __init__(self, query: str, *args: object, **kwargs: object) -> None:
        params: list[object] = []
        fmt = _QueryFormatter(on_param=params.append)
        query = fmt.vformat(query, args, kwargs)

        self._query = query
        self._params = tuple(params)

    @property
    def query(self) -> str:
        """The SQL query string."""
        return self._query

    @property
    def params(self) -> tuple[object, ...]:
        """The query parameters, in the order they appear in the query."""
        return self._params

    # Allows writing `query or "FALSE"`, useful with conditions.
    def __bool__(self) -> bool:
        return bool(self._query)

    @typing.override
    def __eq__(self, value: object, /) -> bool:
        match value:
            case str():
                return self._query == value and not self._params
            case Query(query, params):
                return self._query == query and self._params == params
            case _:
                return False

    @typing.override
    def __hash__(self) -> int:
        return hash(tuple(self)) if self._params else hash(self._query)

    def __iter__(self) -> T.Iterator[T.Any]:
        """Unwrap the query and its parameters to pass them as arguments."""
        yield self._query
        yield from self._params

    @classmethod
    def _new(cls, query: str, params: tuple[object, ...]) -> T.Self:
        """Initialize a new instance manually (without calling `__init__`)."""
        obj = object.__new__(cls)
        obj._params = params  # noqa: SLF001
        obj._query = query  # noqa: SLF001
        return obj

    def transform[**P](
        self,
        func: T.Callable[T.Concatenate[str, P], str],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T.Self:
        """Create a new query by transforming this one.

        Args:
            func: Function to apply on query string.
            args: Additional positional arguments for `func`.
            kwargs: Additional keyword arguments for `func`.

        Returns:
            New query with transformed query string and the same parameters.
        """
        query = func(self._query, *args, **kwargs)
        return self._new(query, self._params)

    @classmethod
    def join(
        cls,
        queries: T.Iterable[Query],
        *,
        delim: str = " ",
        parenthesize: bool = False,
    ) -> T.Self:
        """Create a new query by concatenating multiple subqueries.

        Args:
            queries: Subqueries to concatenate.
            delim: Delimiter to insert between every two query strings.
            parenthesize: Whether to wrap subqueries in parentheses.

        Returns:
            The concatenated query. It holds parameters from all the subqueries.
        """

        # Ensure there are spaces around delim.
        if not delim.startswith(" "):
            delim = f" {delim}"
        if not delim.endswith(" "):
            delim = f"{delim} "

        # Unzip query strings and parameters from queries.
        query, params = zip(
            ("", ()),  # otherwise error when there are no queries
            *((q.query, q.params) for q in queries),
            strict=True,
        )

        # Filter out blank queries.
        query = filter(None, query)

        if parenthesize:
            query = map("({})".format, query)

        return cls._new(
            query=delim.join(query),
            params=tuple(itertools.chain.from_iterable(params)),
        )

    @classmethod
    def any(
        cls,
        queries: T.Iterable[Query],
    ) -> T.Self:
        """Join multiple query conditions with `OR`.

        Returns `FALSE` if no queries are given.
        """
        return cls.join(
            queries,
            delim="OR",
            parenthesize=True,
        ) or cls("FALSE")

    @classmethod
    def all(
        cls,
        queries: T.Iterable[Query],
    ) -> T.Self:
        """Join multiple query conditions with `AND`.

        Returns `TRUE` if no queries are given.
        """
        return cls.join(
            queries,
            delim="AND",
            parenthesize=True,
        ) or cls("TRUE")
