-- Computer Hub Check-in schema (SQLite)

DROP TABLE IF EXISTS reservations;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS stations;
DROP TABLE IF EXISTS visitors;

CREATE TABLE visitors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name   TEXT    NOT NULL,
    email       TEXT    UNIQUE,
    phone       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE stations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    label       TEXT    NOT NULL UNIQUE,      -- e.g. "PC-01"
    kind        TEXT    NOT NULL DEFAULT 'desktop'
                        CHECK (kind IN ('desktop', 'laptop', 'printer')),
    active      INTEGER NOT NULL DEFAULT 1
);

-- A session is one visit at one station: open while ended_at IS NULL.
CREATE TABLE sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    visitor_id  INTEGER NOT NULL REFERENCES visitors(id),
    station_id  INTEGER NOT NULL REFERENCES stations(id),
    purpose     TEXT,
    started_at  TEXT    NOT NULL,
    ended_at    TEXT
);

-- At most one open session per station and per visitor.
CREATE UNIQUE INDEX one_open_session_per_station
    ON sessions(station_id) WHERE ended_at IS NULL;
CREATE UNIQUE INDEX one_open_session_per_visitor
    ON sessions(visitor_id) WHERE ended_at IS NULL;

CREATE TABLE reservations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    visitor_id  INTEGER NOT NULL REFERENCES visitors(id),
    station_id  INTEGER NOT NULL REFERENCES stations(id),
    starts_at   TEXT    NOT NULL,
    ends_at     TEXT    NOT NULL,
    cancelled   INTEGER NOT NULL DEFAULT 0,
    CHECK (ends_at > starts_at)
);

CREATE INDEX reservations_by_station ON reservations(station_id, starts_at);
