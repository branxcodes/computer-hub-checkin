"""Database connection handling.

One SQLite connection is opened per request and stored on Flask's `g`
object, then closed automatically when the request ends.
"""
import sqlite3
from pathlib import Path

import click
from flask import current_app, g

SCHEMA = Path(__file__).with_name("schema.sql")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row          # rows behave like dicts
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    get_db().executescript(SCHEMA.read_text())


@click.command("init-db")
def init_db_command() -> None:
    """Create (or reset) the database tables."""
    init_db()
    click.echo("Database initialized.")


@click.command("seed")
def seed_command() -> None:
    """Add sample stations so the app is usable right away."""
    db = get_db()
    for n in range(1, 9):
        db.execute(
            "INSERT OR IGNORE INTO stations (label, kind) VALUES (?, ?)",
            (f"PC-{n:02d}", "desktop"),
        )
    db.execute("INSERT OR IGNORE INTO stations (label, kind) VALUES ('LAP-01', 'laptop')")
    db.commit()
    click.echo("Sample stations added.")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)
