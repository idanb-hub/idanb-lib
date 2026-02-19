from __future__ import annotations

import abc
import enum

import pydantic

from analytics.connectors.trino import TrinoConfig
from idanb import utils
from idanb.utils.config import CONFIG


class Host(enum.StrEnum):
    SHORT_QUERIES = enum.auto()
    LONG_QUERIES = enum.auto()


class Catalog(enum.StrEnum):
    FLOWS = enum.auto()
    OPENSEARCH = enum.auto()


class DataPlatformConfigHosts(
    utils.enums.to_dataclass(Host, str),
    metaclass=abc.ABCMeta,
):
    pass


class DataPlatformConfigCatalogs(
    utils.enums.to_dataclass(Catalog, str),
    metaclass=abc.ABCMeta,
):
    pass


@CONFIG.register("data_platform")
@pydantic.dataclasses.dataclass()
class DataPlatformConfig:
    hosts: DataPlatformConfigHosts
    port: int
    catalogs: DataPlatformConfigCatalogs
    schema: str
    http_scheme: str
    auth_username: str
    auth_password: str

    def select(self, host: Host, catalog: Catalog) -> TrinoConfig:
        return TrinoConfig(
            host=getattr(self.hosts, host),
            port=self.port,
            catalog=getattr(self.catalogs, catalog),
            schema=self.schema,
            http_scheme=self.http_scheme,
            auth_username=self.auth_username,
            auth_password=self.auth_password,
        )
