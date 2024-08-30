from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, cast

from litestar.constants import HTTP_RESPONSE_START
from litestar.exceptions import ImproperlyConfiguredException
from litestar.utils.dataclass import simple_asdict
from oracledb import create_pool_async as oracledb_create_pool
from oracledb.connection import AsyncConnection
from oracledb.pool import AsyncConnectionPool

from litestar_oracledb._utils import delete_scope_state, get_scope_state, set_scope_state
from litestar_oracledb.config._common import (
    CONNECTION_SCOPE_KEY,
    SESSION_TERMINUS_ASGI_EVENTS,
    GenericDatabaseConfig,
    GenericPoolConfig,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Coroutine
    from typing import Any

    from litestar import Litestar
    from litestar.datastructures.state import State
    from litestar.types import Message, Scope


def default_handler_maker(
    connection_scope_key: str = CONNECTION_SCOPE_KEY,
) -> Callable[[Message, Scope], Coroutine[Any, Any, None]]:
    """Set up the handler to issue a transaction commit or rollback based on specified status codes
    Args:
        connection_scope_key: The key to use within the application state

    Returns:
        The handler callable
    """

    async def handler(message: Message, scope: Scope) -> None:
        """Handle commit/rollback, closing and cleaning up sessions before sending.

        Args:
            message: ASGI-``Message``
            scope: An ASGI-``Scope``

        Returns:
            None
        """
        connection = cast("AsyncConnection | None", get_scope_state(scope, connection_scope_key))
        if connection is not None and message["type"] in SESSION_TERMINUS_ASGI_EVENTS and connection._impl is not None:  # noqa: SLF001
            # checks to to see if connected without raising an exception: https://github.com/oracle/python-oracledb/blob/main/src/oracledb/connection.py#L80
            if connection._impl is not None:  # noqa: SLF001
                await connection.close()
            delete_scope_state(scope, connection_scope_key)

    return handler


def autocommit_handler_maker(
    commit_on_redirect: bool = False,
    extra_commit_statuses: set[int] | None = None,
    extra_rollback_statuses: set[int] | None = None,
    connection_scope_key: str = CONNECTION_SCOPE_KEY,
) -> Callable[[Message, Scope], Coroutine[Any, Any, None]]:
    """Set up the handler to issue a transaction commit or rollback based on specified status codes
    Args:
        commit_on_redirect: Issue a commit when the response status is a redirect (``3XX``)
        extra_commit_statuses: A set of additional status codes that trigger a commit
        extra_rollback_statuses: A set of additional status codes that trigger a rollback
        connection_scope_key: The key to use within the application state

    Returns:
        The handler callable
    """
    if extra_commit_statuses is None:
        extra_commit_statuses = set()

    if extra_rollback_statuses is None:
        extra_rollback_statuses = set()

    if len(extra_commit_statuses & extra_rollback_statuses) > 0:
        msg = "Extra rollback statuses and commit statuses must not share any status codes"
        raise ValueError(msg)

    commit_range = range(200, 400 if commit_on_redirect else 300)

    async def handler(message: Message, scope: Scope) -> None:
        """Handle commit/rollback, closing and cleaning up sessions before sending.

        Args:
            message: ASGI-``Message``
            scope: An ASGI-``Scope``

        Returns:
            None
        """
        connection = cast("AsyncConnection | None", get_scope_state(scope, connection_scope_key))
        try:
            if connection is not None and message["type"] == HTTP_RESPONSE_START and connection._impl is not None:  # noqa: SLF001
                if (message["status"] in commit_range or message["status"] in extra_commit_statuses) and message[
                    "status"
                ] not in extra_rollback_statuses:
                    await connection.commit()
                else:
                    await connection.rollback()
        finally:
            # checks to to see if connected without raising an exception: https://github.com/oracle/python-oracledb/blob/main/src/oracledb/connection.py#L80
            if (
                connection is not None
                and message["type"] in SESSION_TERMINUS_ASGI_EVENTS
                and connection._impl is not None  # noqa: SLF001
            ):
                await connection.close()
                delete_scope_state(scope, connection_scope_key)

    return handler


@dataclass
class AsyncPoolConfig(GenericPoolConfig[AsyncConnectionPool, AsyncConnection]):
    """Async Oracle Pool Config"""


@dataclass
class AsyncDatabaseConfig(GenericDatabaseConfig[AsyncConnectionPool, AsyncConnection]):
    """Async Oracle database Configuration."""

    pool_config: AsyncPoolConfig | None = None
    """Oracle Pool configuration"""

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.before_send_handler is None:
            self.before_send_handler = default_handler_maker(connection_scope_key=self.connection_scope_key)
        if self.before_send_handler == "autocommit":
            self.before_send_handler = autocommit_handler_maker(connection_scope_key=self.connection_scope_key)
        if self.before_send_handler == "autocommit_include_redirects":
            self.before_send_handler = autocommit_handler_maker(
                connection_scope_key=self.connection_scope_key,
                commit_on_redirect=True,
            )

    @property
    def pool_config_dict(self) -> dict[str, Any]:
        """Return the pool configuration as a dict.

        Returns:
            A string keyed dict of config kwargs for the Asyncpg :func:`create_pool <oracledb.pool.create_pool>`
            function.
        """
        if self.pool_config is not None:
            return simple_asdict(self.pool_config, exclude_empty=True, convert_nested=False)
        msg = "'pool_config' methods can not be used when a 'pool_instance' is provided."
        raise ImproperlyConfiguredException(msg)

    @property
    def signature_namespace(self) -> dict[str, Any]:
        """Return the plugin's signature namespace.

        Returns:
            A string keyed dict of names to be added to the namespace for signature forward reference resolution.
        """
        return {
            "AsyncConnection": AsyncConnection,
            "AsyncConnectionPool": AsyncConnectionPool,
        }

    async def create_pool(self) -> AsyncConnectionPool:
        """Return a pool. If none exists yet, create one.

        Returns:
            Getter that returns the pool instance used by the plugin.
        """
        if self.pool_instance is not None:
            return self.pool_instance

        if self.pool_config is None:
            msg = "One of 'pool_config' or 'pool_instance' must be provided."
            raise ImproperlyConfiguredException(msg)

        pool_config = self.pool_config_dict
        self.pool_instance = oracledb_create_pool(**pool_config)
        if self.pool_instance is None:
            msg = "Could not configure the 'pool_instance'. Please check your configuration."
            raise ImproperlyConfiguredException(msg)
        return self.pool_instance

    @asynccontextmanager
    async def lifespan(
        self,
        app: Litestar,
    ) -> AsyncGenerator[None, None]:
        db_pool = await self.create_pool()
        app.state.update({self.pool_app_state_key: db_pool})
        try:
            yield
        finally:
            await db_pool.close()

    async def provide_connection(
        self,
        state: State,
        scope: Scope,
    ) -> AsyncGenerator[AsyncConnection, None]:
        """Create a connection instance.

        Args:
            state: The ``Litestar.state`` instance.
            scope: The current connection's scope.

        Returns:
            A connection instance.
        """
        connection = cast(
            "Optional[AsyncConnection]",
            get_scope_state(scope, self.connection_scope_key),
        )
        if connection is None:
            pool = cast("AsyncConnectionPool", state.get(self.pool_app_state_key))

            async with pool.acquire() as connection:
                set_scope_state(scope, self.connection_scope_key, connection)
                yield connection
