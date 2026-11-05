from datetime import datetime, timedelta

import pytest

from hub import create_app
from hub.db import get_db, init_db


class Clock:
    """A fake clock tests can move forward."""

    def __init__(self, start: datetime):
        self.t = start

    def __call__(self) -> datetime:
        return self.t

    def advance(self, **kw) -> None:
        self.t += timedelta(**kw)


@pytest.fixture
def clock():
    return Clock(datetime(2026, 11, 5, 9, 0, 0))


@pytest.fixture
def app(tmp_path, clock):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite"), "NOW": clock})
    with app.app_context():
        init_db()
        db = get_db()
        db.executemany("INSERT INTO stations (label) VALUES (?)", [("PC-01",), ("PC-02",)])
        db.execute("INSERT INTO visitors (full_name, email) VALUES ('Amina Nakato', 'amina@example.org')")
        db.execute("INSERT INTO visitors (full_name, email) VALUES ('Joseph Okello', 'joseph@example.org')")
        db.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
