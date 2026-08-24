from __future__ import annotations

import typing_extensions as T
import polars as pl

# Maps SQL types to Python (either polars dtype or constructor function).
DTYPES: dict[str, type[pl.DataType] | T.Callable[[T.Any], object]] = {
    "bigint": pl.Int64,
    "boolean": pl.Boolean,
    "double": pl.Float64,
    "integer": pl.Int32,
    "ipaddress": pl.String,  # ipaddress.ip_address
    "varchar": pl.String,
    # NOTE: Timestamps are left to be auto-inferred, which preserves time zones.
}


def is_polars_dtype(obj: object) -> T.TypeGuard[type[pl.DataType]]:
    return isinstance(obj, type) and issubclass(obj, pl.DataType)


POLARS_DTYPES = {
    name: (dt if is_polars_dtype(dt) else pl.Object)
    for name, dt in DTYPES.items()
}

PYTHON_DTYPES = {
    name: dt for name, dt in DTYPES.items() if not is_polars_dtype(dt)
}


def rows_to_polars(
    rows: T.Iterable[list[object]],
    types: T.Mapping[str, str],
) -> pl.DataFrame:
    """Create a DataFrame from rows returned by a query.

    Args:
        rows: The rows, as they were returned by the Trino connector.
        types: Map from column names to their SQL types.

    Returns:
        DataFrame with converted data types (see `DTYPES`).
    """
    return pl.DataFrame(
        data=rows,
        schema={
            name: POLARS_DTYPES.get(sql_type)
            for name, sql_type in types.items()
        },
        orient="row",
    ).with_columns(
        pl.col(name).map_elements(PYTHON_DTYPES[sql_type], pl.Object)
        for name, sql_type in types.items()
        if sql_type in PYTHON_DTYPES
    )
