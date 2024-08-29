from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generator, Optional, cast

from litestar.constants import HTTP_RESPONSE_START
from litestar.exceptions import ImproperlyConfiguredException
from litestar.types import Empty
from litestar.utils.dataclass import simple_asdict
from oracledb import create_pool as oracledb_create_pool
from oracledb.connection import Connection
from oracledb.pool import ConnectionPool

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
    from litestar.types import EmptyType, Message, Scope


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
        connection = cast("Connection | None", get_scope_state(scope, connection_scope_key))
        if connection and message["type"] in SESSION_TERMINUS_ASGI_EVENTS:
            connection.close()
            delete_scope_state(scope, connection_scope_key)

    return handler


def autocommit_handler_maker(
    commit_on_redirect: bool = False,
    extra_commit_statuses: set[int] | None = None,
    extra_rollback_statuses: set[int] | None = None,
    connection_scope_key: str = CONNECTION_SCOPE_KEY,
) -> Callable[[Message, Scope], None]:
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

    def handler(message: Message, scope: Scope) -> None:
        """Handle commit/rollback, closing and cleaning up sessions before sending.

        Args:
            message: ASGI-``Message``
            scope: An ASGI-``Scope``

        Returns:
            None
        """
        connection = cast("Connection | None", get_scope_state(scope, connection_scope_key))
        try:
            if connection is not None and message["type"] == HTTP_RESPONSE_START:
                if (message["status"] in commit_range or message["status"] in extra_commit_statuses) and message[
                    "status"
                ] not in extra_rollback_statuses:
                    connection.commit()
                else:
                    connection.rollback()
        finally:
            if connection and message["type"] in SESSION_TERMINUS_ASGI_EVENTS:
                connection.close()
                delete_scope_state(scope, connection_scope_key)

    return handler


@dataclass
class SyncPoolConfig(GenericPoolConfig[ConnectionPool, Connection]):
    """Sync Oracle Pool Config"""


@dataclass
class SyncDatabaseConfig(GenericDatabaseConfig[ConnectionPool, Connection]):
    """Oracle database Configuration."""

    pool_config: SyncPoolConfig | None | EmptyType = Empty
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
        if self.pool_config is not None and self.pool_config != Empty:
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
            "Connection": Connection,
            "ConnectionPool": ConnectionPool,
        }

    def create_pool(self) -> ConnectionPool:
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
        db_pool = self.create_pool()
        app.state.update({self.pool_app_state_key: db_pool})
        try:
            yield
        finally:
            db_pool.close(force=True)

    def provide_connection(
        self,
        state: State,
        scope: Scope,
    ) -> Generator[Connection, None, None]:
        """Create a connection instance.

        Args:
            state: The ``Litestar.state`` instance.
            scope: The current connection's scope.

        Returns:
            A connection instance.
        """
        connection = cast(
            "Optional[Connection]",
            get_scope_state(scope, self.connection_scope_key),
        )
        if connection is None:
            pool = cast("ConnectionPool", state.get(self.pool_app_state_key))

            with pool.acquire() as connection:
                set_scope_state(scope, self.connection_scope_key, connection)
                yield connection
