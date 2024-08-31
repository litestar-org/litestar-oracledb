from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Sequence, TypeVar, cast

from litestar.plugins import InitPluginProtocol

from litestar_oracledb.exceptions import ImproperConfigurationError

if TYPE_CHECKING:
    from litestar.config.app import AppConfig
    from litestar.types import BeforeMessageSendHookHandler

    from litestar_oracledb.config import AsyncOracleDatabaseConfig, SyncOracleDatabaseConfig


ConfigT = TypeVar("ConfigT", bound="AsyncOracleDatabaseConfig | SyncOracleDatabaseConfig")


class SlotsBase:
    __slots__ = ("_config",)


class OracleDatabasePlugin(InitPluginProtocol, SlotsBase, Generic[ConfigT]):
    """Oracledb plugin."""

    __slots__ = ()

    def __init__(self, config: ConfigT | Sequence[ConfigT]) -> None:
        """Initialize ``oracledb``.

        Args:
            config: configure and start Asyncpg.
        """
        self._config = config

    @property
    def config(self) -> ConfigT | Sequence[ConfigT]:
        """Return the plugin config.

        Returns:
            AsyncpgConfig.
        """
        return self._config

    def _validate_config(self) -> None:
        configs = self._config if isinstance(self._config, Sequence) else [self._config]
        connection_scope_keys = {config.connection_scope_key for config in configs}
        connection_dependency_keys = {config.connection_dependency_key for config in configs}
        pool_state_keys = {config.pool_app_state_key for config in configs}
        if len(configs) > 1 and any(
            len(i) != len(configs) for i in (connection_scope_keys, connection_dependency_keys, pool_state_keys)
        ):
            raise ImproperConfigurationError(
                detail="When using multiple configurations, please ensure the `connection_scope_keys`, `pool_state_keys` and `connection_dependency_keys` settings are unique across all configs.",
            )

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure application for use with Oracle.

        Args:
            app_config: The :class:`AppConfig <.config.app.AppConfig>` instance.
        """
        self._validate_config()
        for config in self._config if isinstance(self._config, Sequence) else [self._config]:
            app_config.dependencies.update(config.dependencies)
            app_config.before_send.append(cast("BeforeMessageSendHookHandler", config.before_send_handler))
            app_config.lifespan.append(config.lifespan)
            app_config.signature_namespace.update(config.signature_namespace)

        return app_config
