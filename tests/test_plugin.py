from contextlib import asynccontextmanager
from functools import partial
from typing import Any, AsyncGenerator

import pytest
from litestar import Litestar, get
from litestar.testing import create_test_client
from oracledb import AsyncConnection

from litestar_oracledb import AsyncDatabaseConfig, OracleDatabasePlugin

pytestmark = pytest.mark.anyio


async def test_lifespan(
    async_config: AsyncDatabaseConfig,
) -> None:
    @get("/")
    async def health_check(db_connection: AsyncConnection) -> float:
        """Check database available and returns random number."""
        with db_connection.cursor() as cursor:
            await cursor.execute("select 1 as the_one from dual")
            r = await cursor.fetchall()
            return r[0]["the_one"]  # type: ignore

    @asynccontextmanager
    async def lifespan(_app: Litestar) -> AsyncGenerator[None, Any]:
        print(1)  # noqa: T201
        yield
        print(2)  # noqa: T201

    oracledb = OracleDatabasePlugin(config=async_config)
    with create_test_client(route_handlers=[health_check], plugins=[oracledb], lifespan=[partial(lifespan)]) as client:
        response = client.get("/")
        assert response.status_code == 200
