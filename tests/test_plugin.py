from contextlib import asynccontextmanager
from functools import partial
from typing import Any, AsyncGenerator

import pytest
from litestar import Litestar, get
from litestar.exceptions import HTTPException
from litestar.testing import create_async_test_client
from oracledb import AsyncConnection, Connection

from litestar_oracledb import OracleDatabasePlugin

pytestmark = pytest.mark.anyio


async def test_lifespan(plugin: OracleDatabasePlugin, oracle_service: None) -> None:
    @get("/async/")
    async def async_health_check(db_connection: AsyncConnection) -> int:
        """Check database available and returns random number."""
        r = await db_connection.fetchall("select 1 as the_one from dual")
        if r:
            return r[0][0]  # type: ignore
        raise HTTPException(detail="error fetching the data", status_code=500)

    @get("/sync/", sync_to_thread=True)
    def sync_health_check(sync_db_connection: Connection) -> int:
        """Check database available and returns random number."""
        with sync_db_connection.cursor() as cursor:
            cursor.execute("select 1 as the_other_one from dual")
            r = cursor.fetchall()
            if r:
                return r[0][0]  # type: ignore
        raise HTTPException(detail="error fetching the other data", status_code=500)

    @asynccontextmanager
    async def lifespan(_app: Litestar) -> AsyncGenerator[None, Any]:
        print(1)  # noqa: T201
        yield
        print(2)  # noqa: T201

    async with create_async_test_client(
        route_handlers=[async_health_check, sync_health_check], plugins=[plugin], lifespan=[partial(lifespan)]
    ) as client:
        # async_r = await client.get("/async/")
        # assert async_r.status_code == 200
        sync_r = await client.get("/sync/")
        assert sync_r.status_code == 200
