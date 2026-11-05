"""Business rules for the hub, kept separate from HTTP so they are easy to test.

Times are stored as ISO-8601 text ("YYYY-MM-DD HH:MM:SS") in hub-local time.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from flask import current_app

from .db import get_db

FMT = "%Y-%m-%d %H:%M:%S"
MAX_RESERVATION = timedelta(hours=3)
# A reservation holds the station for this long after its start time.
NO_SHOW_GRACE = timedelta(minutes=15)


class HubError(Exception):
    """A rule was broken. `status` is the HTTP code the API should return."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def now() -> datetime:
    # Tests can freeze time by setting app.config["NOW"] to a callable.
    clock = current_app.config.get("NOW")
    return clock() if clock else datetime.now().replace(microsecond=0)


def parse_time(value: str, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value).replace(microsecond=0)
    except (TypeError, ValueError):
        raise HubError(f"'{field}' must be an ISO date-time like 2026-11-05T14:30")


def _row(query: str, *args) -> sqlite3.Row | None:
    return get_db().execute(query, args).fetchone()


# ---------------------------------------------------------------- visitors

def register_visitor(full_name: str, email: str | None = None, phone: str | None = None) -> int:
    full_name = (full_name or "").strip()
    if not full_name:
        raise HubError("full_name is required")
    email = (email or "").strip().lower() or None
    try:
        cur = get_db().execute(
            "INSERT INTO visitors (full_name, email, phone) VALUES (?, ?, ?)",
            (full_name, email, phone),
        )
    except sqlite3.IntegrityError:
        raise HubError("a visitor with that email already exists", 409)
    get_db().commit()
    return cur.lastrowid


def find_visitors(term: str) -> list[sqlite3.Row]:
    like = f"%{term.strip()}%"
    return get_db().execute(
        "SELECT * FROM visitors WHERE full_name LIKE ? OR email LIKE ? ORDER BY full_name LIMIT 25",
        (like, like),
    ).fetchall()


def _require_visitor(visitor_id: int) -> sqlite3.Row:
    v = _row("SELECT * FROM visitors WHERE id = ?", visitor_id)
    if v is None:
        raise HubError("visitor not found", 404)
    return v


def _require_station(station_id: int) -> sqlite3.Row:
    s = _row("SELECT * FROM stations WHERE id = ?", station_id)
    if s is None:
        raise HubError("station not found", 404)
    if not s["active"]:
        raise HubError("station is out of service", 409)
    return s


# ---------------------------------------------------------------- stations

def add_station(label: str, kind: str = "desktop") -> int:
    try:
        cur = get_db().execute("INSERT INTO stations (label, kind) VALUES (?, ?)", (label, kind))
    except sqlite3.IntegrityError:
        raise HubError("station label must be unique and kind must be desktop, laptop or printer", 409)
    get_db().commit()
    return cur.lastrowid


def station_board() -> list[dict]:
    """Every station with its live status: free, in_use, or reserved."""
    t = now()
    stations = get_db().execute("SELECT * FROM stations ORDER BY label").fetchall()
    board = []
    for s in stations:
        item = {"id": s["id"], "label": s["label"], "kind": s["kind"], "active": bool(s["active"])}
        session = _row(
            """SELECT se.*, v.full_name FROM sessions se JOIN visitors v ON v.id = se.visitor_id
               WHERE station_id = ? AND ended_at IS NULL""",
            s["id"],
        )
        held = _holding_reservation(s["id"], t)
        if not s["active"]:
            item["status"] = "out_of_service"
        elif session:
            started = datetime.strptime(session["started_at"], FMT)
            item.update(status="in_use", visitor=session["full_name"],
                        minutes=int((t - started).total_seconds() // 60))
        elif held:
            item.update(status="reserved", reserved_for=held["visitor_id"],
                        until=held["ends_at"])
        else:
            item["status"] = "free"
        board.append(item)
    return board


# ------------------------------------------------------------ reservations

def _holding_reservation(station_id: int, t: datetime) -> sqlite3.Row | None:
    """A reservation that currently holds the station (started, within grace or until end)."""
    return _row(
        """SELECT * FROM reservations
           WHERE station_id = ? AND cancelled = 0 AND starts_at <= ? AND ends_at > ?
           ORDER BY starts_at LIMIT 1""",
        station_id, t.strftime(FMT), t.strftime(FMT),
    )


def reserve(visitor_id: int, station_id: int, starts_at: datetime, ends_at: datetime) -> int:
    _require_visitor(visitor_id)
    _require_station(station_id)
    if ends_at <= starts_at:
        raise HubError("ends_at must be after starts_at")
    if ends_at - starts_at > MAX_RESERVATION:
        raise HubError("reservations are limited to 3 hours")
    if starts_at < now() - timedelta(minutes=1):
        raise HubError("cannot reserve in the past")

    # Two intervals overlap when each starts before the other ends.
    clash = _row(
        """SELECT id FROM reservations
           WHERE station_id = ? AND cancelled = 0 AND starts_at < ? AND ends_at > ?""",
        station_id, ends_at.strftime(FMT), starts_at.strftime(FMT),
    )
    if clash:
        raise HubError("station is already reserved for part of that time", 409)

    cur = get_db().execute(
        "INSERT INTO reservations (visitor_id, station_id, starts_at, ends_at) VALUES (?, ?, ?, ?)",
        (visitor_id, station_id, starts_at.strftime(FMT), ends_at.strftime(FMT)),
    )
    get_db().commit()
    return cur.lastrowid


def cancel_reservation(reservation_id: int) -> None:
    cur = get_db().execute("UPDATE reservations SET cancelled = 1 WHERE id = ?", (reservation_id,))
    if cur.rowcount == 0:
        raise HubError("reservation not found", 404)
    get_db().commit()


# ---------------------------------------------------------------- sessions

def check_in(visitor_id: int, station_id: int, purpose: str | None = None) -> int:
    _require_visitor(visitor_id)
    _require_station(station_id)
    t = now()

    held = _holding_reservation(station_id, t)
    if held and held["visitor_id"] != visitor_id:
        started = datetime.strptime(held["starts_at"], FMT)
        # After the grace period an unclaimed reservation is treated as a no-show.
        if t < started + NO_SHOW_GRACE:
            raise HubError("station is reserved for another visitor right now", 409)

    try:
        cur = get_db().execute(
            "INSERT INTO sessions (visitor_id, station_id, purpose, started_at) VALUES (?, ?, ?, ?)",
            (visitor_id, station_id, purpose, t.strftime(FMT)),
        )
    except sqlite3.IntegrityError:
        raise HubError("visitor or station already has an open session", 409)
    get_db().commit()
    return cur.lastrowid


def check_out(session_id: int) -> dict:
    s = _row("SELECT * FROM sessions WHERE id = ?", session_id)
    if s is None:
        raise HubError("session not found", 404)
    if s["ended_at"]:
        raise HubError("session already checked out", 409)
    t = now()
    get_db().execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (t.strftime(FMT), session_id))
    get_db().commit()
    minutes = int((t - datetime.strptime(s["started_at"], FMT)).total_seconds() // 60)
    return {"session_id": session_id, "minutes": minutes}


def open_session_for_station(station_id: int) -> sqlite3.Row | None:
    return _row("SELECT * FROM sessions WHERE station_id = ? AND ended_at IS NULL", station_id)


# ----------------------------------------------------------------- reports

def daily_report(day: str) -> dict:
    """Usage totals for one calendar day (YYYY-MM-DD)."""
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        raise HubError("day must look like 2026-11-05")
    rows = get_db().execute(
        """SELECT se.visitor_id, se.purpose,
                  (julianday(COALESCE(se.ended_at, ?)) - julianday(se.started_at)) * 1440 AS minutes
           FROM sessions se WHERE date(se.started_at) = ?""",
        (now().strftime(FMT), day),
    ).fetchall()
    purposes: dict[str, int] = {}
    for r in rows:
        key = r["purpose"] or "unspecified"
        purposes[key] = purposes.get(key, 0) + 1
    total = sum(r["minutes"] for r in rows)
    return {
        "day": day,
        "sessions": len(rows),
        "unique_visitors": len({r["visitor_id"] for r in rows}),
        "total_minutes": round(total),
        "average_minutes": round(total / len(rows)) if rows else 0,
        "by_purpose": purposes,
    }
