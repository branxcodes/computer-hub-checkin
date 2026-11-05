"""JSON REST API, mounted at /api."""
from flask import Blueprint, jsonify, request

from . import services as svc

bp = Blueprint("api", __name__, url_prefix="/api")


def body() -> dict:
    return request.get_json(silent=True) or {}


def need_int(data: dict, field: str) -> int:
    try:
        return int(data[field])
    except (KeyError, TypeError, ValueError):
        raise svc.HubError(f"'{field}' is required and must be a number")


@bp.get("/health")
def health():
    return {"status": "ok"}


@bp.post("/visitors")
def create_visitor():
    d = body()
    vid = svc.register_visitor(d.get("full_name"), d.get("email"), d.get("phone"))
    return {"id": vid}, 201


@bp.get("/visitors")
def search_visitors():
    return jsonify([dict(r) for r in svc.find_visitors(request.args.get("q", ""))])


@bp.post("/stations")
def create_station():
    d = body()
    if not d.get("label"):
        raise svc.HubError("label is required")
    return {"id": svc.add_station(d["label"], d.get("kind", "desktop"))}, 201


@bp.get("/stations")
def stations():
    return jsonify(svc.station_board())


@bp.post("/sessions")
def check_in():
    d = body()
    sid = svc.check_in(need_int(d, "visitor_id"), need_int(d, "station_id"), d.get("purpose"))
    return {"id": sid}, 201


@bp.post("/sessions/<int:session_id>/checkout")
def check_out(session_id: int):
    return svc.check_out(session_id)


@bp.post("/reservations")
def reserve():
    d = body()
    rid = svc.reserve(
        need_int(d, "visitor_id"),
        need_int(d, "station_id"),
        svc.parse_time(d.get("starts_at"), "starts_at"),
        svc.parse_time(d.get("ends_at"), "ends_at"),
    )
    return {"id": rid}, 201


@bp.delete("/reservations/<int:reservation_id>")
def cancel(reservation_id: int):
    svc.cancel_reservation(reservation_id)
    return "", 204


@bp.get("/reports/daily")
def daily():
    day = request.args.get("day") or svc.now().strftime("%Y-%m-%d")
    return svc.daily_report(day)
