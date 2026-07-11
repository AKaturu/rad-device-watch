from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from rad_device_watch.database import Database


@pytest.fixture
def db(tmp_path: Path) -> Generator[Database, None, None]:
    database = Database(tmp_path / "test.db")
    database.connect()
    database.init_schema()
    yield database
    database.close()
