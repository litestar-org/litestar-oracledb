from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec
from litestar import Controller, Litestar, get
from litestar.exceptions import InternalServerException

from litestar_oracledb import AsyncDatabaseConfig, AsyncPoolConfig, OracleDatabasePlugin

if TYPE_CHECKING:
    from oracledb import AsyncConnection


class HealthCheck(msgspec.Struct):
    status: str


class SampleController(Controller):
    @get(path="/sample")
    async def sample_route(self, db_connection: AsyncConnection) -> HealthCheck:
        """Check database available and returns app config info."""
        cursor = db_connection.cursor()
        await cursor.execute("select 1 from dual")
        result = await cursor.fetchone()
        if result:
            return HealthCheck(status="online")
        raise InternalServerException


oracledb = OracleDatabasePlugin(
    config=AsyncDatabaseConfig(
        pool_config=AsyncPoolConfig(user="app", password="super-secret", dsn="localhost:1521/freepdb1")  # noqa: S106
    )
)
app = Litestar(plugins=[oracledb], route_handlers=[SampleController])
