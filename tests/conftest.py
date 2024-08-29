from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Generator, cast

import pytest
from examples.basic import SampleController
from litestar import Litestar
from oracledb.pool import AsyncConnectionPool, ConnectionPool, create_pool, create_pool_async
from pytest import FixtureRequest

if TYPE_CHECKING:
    from pathlib import Path


from litestar_oracledb import (
    AsyncDatabaseConfig,
    OracleDatabasePlugin,
    SyncDatabaseConfig,
)

here = Path(__file__).parent


pytestmark = pytest.mark.anyio
pytest_plugins = [
    "pytest_databases.docker",
    "pytest_databases.docker.oracle",
]


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(name="async_connection_pool", scope="session")
async def async_connection_pool(
    oracle_docker_ip: str,
    oracle_user: str,
    oracle_password: str,
    oracle_service_name: str,
    oracle_port: int,
    oracle_service: None,
) -> AsyncGenerator[AsyncConnectionPool, None]:
    """App fixture.

    Returns:
        An application instance, configured via plugin.
    """
    yield create_pool_async(
        user=oracle_user,
        password=oracle_password,
        host=oracle_docker_ip,
        port=oracle_port,
        service_name=oracle_service_name,
    )


@pytest.fixture(name="sync_connection_pool", scope="session")
async def sync_connection_pool(
    oracle_docker_ip: str,
    oracle_user: str,
    oracle_password: str,
    oracle_service_name: str,
    oracle_port: int,
    oracle_service: None,
) -> AsyncGenerator[ConnectionPool, None]:
    """App fixture.

    Returns:
        An application instance, configured via plugin.
    """
    yield create_pool(
        user=oracle_user,
        password=oracle_password,
        host=oracle_docker_ip,
        port=oracle_port,
        service_name=oracle_service_name,
    )


@pytest.fixture(name="sync_plugin")
def sync_config(sync_connection_pool: ConnectionPool) -> Generator[SyncDatabaseConfig, None, None]:
    """App fixture.

    Returns:
        An application instance, configured via plugin.
    """

    yield SyncDatabaseConfig(
        pool_instance=sync_connection_pool,
    )


@pytest.fixture(name="async_config")
def async_config(async_connection_pool: AsyncConnectionPool) -> Generator[AsyncDatabaseConfig, None, None]:
    """App fixture.

    Returns:
        An application instance, configured via plugin.
    """

    yield AsyncDatabaseConfig(
        pool_instance=async_connection_pool,
    )


@pytest.fixture(
    name="plugin",
    params=[
        pytest.param(
            "async_config",
        ),
        pytest.param(
            "sync_config",
        ),
    ],
)
async def plugin(request: FixtureRequest) -> AsyncGenerator[OracleDatabasePlugin, None]:
    """App fixture.

    Returns:
        An application instance, configured via plugin.
    """
    config = cast("AsyncDatabaseConfig|SyncDatabaseConfig", request.getfixturevalue(request.param))
    yield OracleDatabasePlugin(
        config=config,
    )


@pytest.fixture(name="app")
def fx_app(plugin: OracleDatabasePlugin) -> Generator[Litestar, None, None]:
    """App fixture.

    Returns:
        An application instance, configured via plugin.
    """
    yield Litestar(plugins=[plugin], route_handlers=[SampleController])
