# Computer Hub Check-in

A front-desk system for a community technology center: register visitors, check them in and out of computer stations, take reservations, and see daily usage at a glance.

I'm building toward founding a community Computer Hub that gives people free access to computers, internet and digital-literacy training. This project models the day-to-day operations such a hub needs.

![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![Flask](https://img.shields.io/badge/flask-3.x-black) ![SQLite](https://img.shields.io/badge/db-SQLite-lightgrey)

## Features

- **Live station board.** Every station shows as free, in use (with who and for how long), reserved, or out of service.
- **Check-in / check-out** with a purpose tag (job search, schoolwork, class, printing).
- **Reservations** with overlap detection, a 3-hour limit, and a 15-minute no-show grace period after which the station is released.
- **Guard rails in the database.** Partial unique indexes guarantee one open session per station and per visitor, even under concurrent requests.
- **Daily report** of sessions, unique visitors, total and average minutes, and a breakdown by purpose.
- **JSON REST API** plus a server-rendered front-desk page.
- **18 automated tests** using a fake clock, so time-based rules are tested exactly.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app hub init-db
flask --app hub seed          # adds PC-01 … PC-08 and LAP-01
flask --app hub run --debug
```

Open http://127.0.0.1:5000 for the front desk.

Run the tests:

```bash
pytest
```

## API

| Method | Path | Body / query | Notes |
|---|---|---|---|
| GET | `/api/health` | | liveness check |
| POST | `/api/visitors` | `full_name`, `email?`, `phone?` | 409 on duplicate email |
| GET | `/api/visitors?q=` | | search by name or email |
| POST | `/api/stations` | `label`, `kind?` | kind: desktop, laptop, printer |
| GET | `/api/stations` | | live board with status |
| POST | `/api/sessions` | `visitor_id`, `station_id`, `purpose?` | check in |
| POST | `/api/sessions/<id>/checkout` | | returns minutes used |
| POST | `/api/reservations` | `visitor_id`, `station_id`, `starts_at`, `ends_at` | ISO times |
| DELETE | `/api/reservations/<id>` | | cancel |
| GET | `/api/reports/daily?day=YYYY-MM-DD` | | usage summary |

Errors come back as `{"error": "..."}` with a meaningful status code (400, 404 or 409).

```bash
curl -X POST localhost:5000/api/visitors -H 'Content-Type: application/json' \
     -d '{"full_name":"Amina Nakato","email":"amina@example.org"}'
curl -X POST localhost:5000/api/sessions -H 'Content-Type: application/json' \
     -d '{"visitor_id":1,"station_id":1,"purpose":"job search"}'
```

## Design

```
hub/
  __init__.py   app factory, blueprint registration, error handler
  db.py         per-request SQLite connection, init-db and seed commands
  schema.sql    tables, CHECK constraints, partial unique indexes
  services.py   all business rules (no HTTP code here)
  api.py        JSON endpoints (thin: parse input, call services)
  web.py        front-desk pages
tests/          pytest suite with a controllable clock
```

- **Business logic lives in `services.py`**, not in the routes, so the API and the web pages share the same rules and everything can be tested directly.
- **Overlap check:** two time ranges overlap when `a.start < b.end AND a.end > b.start`. Back-to-back bookings are allowed.
- **Rules are enforced in the database where possible**, not only in Python. Partial unique indexes (`WHERE ended_at IS NULL`) stop double check-ins even if two requests arrive at the same moment.
- **Time is injectable:** `services.now()` reads a clock from config, which lets the tests fast-forward through the no-show grace period.

## Roadmap

- Staff login and roles (front desk vs. admin)
- Weekly and monthly reports with CSV export
- Waitlist when all stations are busy
- Postgres support for multi-site hubs

## License

MIT
