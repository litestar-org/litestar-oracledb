from __future__ import annotations

import pytest

pytestmark = pytest.mark.anyio
pytest_plugins = [
    "tests.database_fixtures",
    "pytest_databases.docker",
    "pytest_databases.docker.oracle",
]


@pytest.fixture(scope="session", autouse=True)
def anyio_backend() -> str:
    return "asyncio"
