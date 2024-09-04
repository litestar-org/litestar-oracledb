from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import pytest
from examples.basic import SampleController
from litestar import Litestar
from oracledb import ConnectionPool, create_pool

from litestar_oracledb import (
    AsyncOracleDatabaseConfig,
    AsyncOraclePoolConfig,
    OracleDatabasePlugin,
    SyncOracleDatabaseConfig,
)

if TYPE_CHECKING:
    from pathlib import Path


here = Path(__file__).parent


@pytest.fixture(name="sync_connection_pool", scope="session")
def sync_connection_pool(
    oracle_docker_ip: str,
    oracle_user: str,
    oracle_password: str,
    oracle_service_name: str,
    oracle_port: int,
    oracle_service: None,
) -> Generator[ConnectionPool, None, None]:
    """App fixture.

    Returns:
        An application instance, configured via plugin.
    """
    yield create_pool(
        user=oracle_user,
        password=oracle_password,
        host="127.0.0.1",
        port=oracle_port,
        service_name=oracle_service_name,
    )


@pytest.fixture(name="sync_config", scope="session")
def sync_config(sync_connection_pool: ConnectionPool) -> Generator[SyncOracleDatabaseConfig, None, None]:
    """App fixture.

    Returns:
        An application instance, configured via plugin.
    """

    yield SyncOracleDatabaseConfig(
        pool_app_state_key="sync_db_pool",
        pool_dependency_key="sync_db_pool",
        connection_dependency_key="sync_db_connection",
        pool_instance=sync_connection_pool,
    )


@pytest.fixture(name="async_config")
async def async_config(
    oracle_docker_ip: str,
    oracle_user: str,
    oracle_password: str,
    oracle_service_name: str,
    oracle_port: int,
    oracle_service: None,
) -> AsyncGenerator[AsyncOracleDatabaseConfig, None]:
    """App fixture.

    Returns:
        An application instance, configured via plugin.
    """
    config = AsyncOracleDatabaseConfig(
        pool_config=AsyncOraclePoolConfig(
            user=oracle_user,
            password=oracle_password,
            host="127.0.0.1",
            port=oracle_port,
            service_name=oracle_service_name,
        ),
    )
    _ = await config.create_pool()
    yield config


@pytest.fixture(name="plugin")
async def plugin(
    async_config: AsyncOracleDatabaseConfig,
    sync_config: SyncOracleDatabaseConfig,
    oracle_service: None,
) -> AsyncGenerator[OracleDatabasePlugin, None]:
    """App fixture.

    Returns:
        An application instance, configured via plugin.
    """
    yield OracleDatabasePlugin(
        config=[async_config, sync_config],
    )


@pytest.fixture(name="app")
async def fx_app(plugin: OracleDatabasePlugin) -> AsyncGenerator[Litestar, None]:
    """App fixture.

    Returns:
        An application instance, configured via plugin.
    """

    yield Litestar(
        plugins=[plugin],
        route_handlers=[SampleController],
    )
