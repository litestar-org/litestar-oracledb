from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import Controller, Litestar, Request, get

from litestar_oracledb import AsyncDatabaseConfig, AsyncPoolConfig, OracleDatabasePlugin

if TYPE_CHECKING:
    from oracledb import AsyncConnection


class SampleController(Controller):
    @get(path="/")
    async def sample_route(self, request: Request, db_connection: AsyncConnection) -> dict[str, str]:
        """Check database available and returns app config info."""
        with db_connection.cursor() as cursor:
            await cursor.execute("select 'a database value' a_column from dual")
            result = await cursor.fetchone()
            request.logger.info(result[0])
            if result:
                return {"a_column": result[0]}
        return {"a_column": "dunno"}


oracledb = OracleDatabasePlugin(
    config=AsyncDatabaseConfig(
        pool_config=AsyncPoolConfig(user="system", password="super-secret", dsn="localhost:1513/FREEPDB1")  # noqa: S106
    )
)
app = Litestar(plugins=[oracledb], route_handlers=[SampleController])
