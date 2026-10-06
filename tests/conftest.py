import os
import tempfile

os.environ.setdefault("MAPIS_DATABASE_URL", f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/test.db")

import pytest

from backend.config import Settings
from backend.core.shield import MapisShield
from backend.core.store import MemoryStore


@pytest.fixture
def shield():
    return MapisShield(Settings(redis_url="", model_path="does/not/exist"), MemoryStore())
