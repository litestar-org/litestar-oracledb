from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Generic, Literal, TypeVar, cast

from litestar.constants import HTTP_DISCONNECT, HTTP_RESPONSE_START, WEBSOCKET_CLOSE, WEBSOCKET_DISCONNECT
from litestar.types import Empty
from oracledb import ConnectionPool

if TYPE_CHECKING:
    import ssl
    from collections.abc import Callable
    from typing import Any

    from litestar.datastructures.state import State
    from litestar.types import BeforeMessageSendHookHandler, EmptyType
    from oracledb import AuthMode, ConnectParams, Purity
    from oracledb.connection import AsyncConnection, Connection
    from oracledb.pool import AsyncConnectionPool, ConnectionPool

CONNECTION_SCOPE_KEY = "_oracledb_db_connection"
SESSION_TERMINUS_ASGI_EVENTS = {HTTP_RESPONSE_START, HTTP_DISCONNECT, WEBSOCKET_DISCONNECT, WEBSOCKET_CLOSE}
T = TypeVar("T")

"""Path to the Alembic templates."""
ConnectionT = TypeVar("ConnectionT", bound="Connection | AsyncConnection")
PoolT = TypeVar("PoolT", bound="ConnectionPool | AsyncConnectionPool")


@dataclass
class GenericPoolConfig(Generic[PoolT, ConnectionT]):
    conn_class: type[ConnectionT] | EmptyType = Empty
    dsn: str | EmptyType = Empty
    pool: PoolT | EmptyType = Empty
    params: ConnectParams | EmptyType = Empty
    user: str | EmptyType = Empty
    proxy_user: str | EmptyType = Empty
    password: str | EmptyType = Empty
    newpassword: str | EmptyType = Empty
    wallet_password: str | EmptyType = Empty
    access_token: str | tuple | Callable | EmptyType = Empty
    host: str | EmptyType = Empty
    port: int | EmptyType = Empty
    protocol: str | EmptyType = Empty
    https_proxy: str | EmptyType = Empty
    https_proxy_port: int | EmptyType = Empty
    service_name: str | EmptyType = Empty
    sid: str | EmptyType = Empty
    server_type: str | EmptyType = Empty
    cclass: str | EmptyType = Empty
    purity: Purity | EmptyType = Empty
    expire_time: int | EmptyType = Empty
    retry_count: int | EmptyType = Empty
    retry_delay: int | EmptyType = Empty
    tcp_connect_timeout: float | EmptyType = Empty
    ssl_server_dn_match: bool | EmptyType = Empty
    ssl_server_cert_dn: str | EmptyType = Empty
    wallet_location: str | EmptyType = Empty
    events: bool | EmptyType = Empty
    externalauth: bool | EmptyType = Empty
    mode: AuthMode | EmptyType = Empty
    disable_oob: bool | EmptyType = Empty
    stmtcachesize: int | EmptyType = Empty
    edition: str | EmptyType = Empty
    tag: str | EmptyType = Empty
    matchanytag: bool | EmptyType = Empty
    config_dir: str | EmptyType = Empty
    appcontext: list | EmptyType = Empty
    shardingkey: list | EmptyType = Empty
    supershardingkey: list | EmptyType = Empty
    debug_jdwp: str | EmptyType = Empty
    connection_id_prefix: str | EmptyType = Empty
    ssl_context: Any | EmptyType = Empty
    sdu: int | EmptyType = Empty
    pool_boundary: str | EmptyType = Empty
    use_tcp_fast_open: bool | EmptyType = Empty
    ssl_version: ssl.TLSVersion | EmptyType = Empty
    handle: int | EmptyType = Empty


@dataclass
class GenericDatabaseConfig(Generic[PoolT, ConnectionT]):
    """Oracle database Configuration."""

    pool_app_state_key: str = "db_pool"
    """Key under which to store the oracledb pool in the application :class:`State <.datastructures.State>`
    instance.
    """
    pool_dependency_key: str = "db_pool"
    """Key under which to store the oracledb Pool in the application dependency injection map.    """
    connection_dependency_key: str = "db_connection"
    """Key under which to store the oracledb Pool in the application dependency injection map.    """
    connection_scope_key: str = CONNECTION_SCOPE_KEY
    """Key under which to store the entire connection state in the application dependency injection map.    """
    pool_instance: PoolT | None = None
    """Optional pool to use.

    If set, the plugin will use the provided pool rather than instantiate one.
    """
    before_send_handler: BeforeMessageSendHookHandler | None | Literal["autocommit", "autocommit_include_redirects"] = (
        None
    )
    """Handler to call before the ASGI message is sent.

    The handler should handle closing the session stored in the ASGI scope, if it's still open, and committing and
    uncommitted data.
    """
    _CONNECTION_SCOPE_KEY_REGISTRY: ClassVar[set[str]] = field(init=False, default=cast("set[str]", set()))
    """Internal counter for ensuring unique identification of session scope keys in the class."""
    _POOL_APP_STATE_KEY_REGISTRY: ClassVar[set[str]] = field(init=False, default=cast("set[str]", set()))
    """Internal counter for ensuring unique identification of engine app state keys in the class."""

    def _ensure_unique(self, registry_name: str, key: str, new_key: str | None = None, _iter: int = 0) -> str:
        new_key = new_key if new_key is not None else key
        if new_key in getattr(self.__class__, registry_name, {}):
            _iter += 1
            new_key = self._ensure_unique(registry_name, key, f"{key}_{_iter}", _iter)
        return new_key

    def __post_init__(self) -> None:
        self.connection_scope_key = self._ensure_unique("_CONNECTION_SCOPE_KEY_REGISTRY", self.connection_scope_key)
        self.pool_app_state_key = self._ensure_unique("_POOL_APP_STATE_KEY_REGISTRY", self.pool_app_state_key)
        self.__class__._CONNECTION_SCOPE_KEY_REGISTRY.add(self.connection_scope_key)  # noqa: SLF001
        self.__class__._POOL_APP_STATE_KEY_REGISTRY.add(self.pool_app_state_key)  # noqa: SLF001

    def provide_pool(self, state: State) -> PoolT:
        """Create a pool instance.

        Args:
            state: The ``Litestar.state`` instance.

        Returns:
            A Pool instance.
        """
        return cast("PoolT", state.get(self.pool_app_state_key))
