"""Front-desk web pages: a live station board plus check-in/out forms."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from . import services as svc

bp = Blueprint("web", __name__)


@bp.get("/")
def board():
    q = request.args.get("q", "").strip()
    matches = svc.find_visitors(q) if q else []
    return render_template("board.html", stations=svc.station_board(), q=q, matches=matches,
                           report=svc.daily_report(svc.now().strftime("%Y-%m-%d")))


@bp.post("/visitors")
def new_visitor():
    try:
        svc.register_visitor(request.form.get("full_name"), request.form.get("email"),
                             request.form.get("phone"))
        flash("Visitor registered.", "ok")
    except svc.HubError as e:
        flash(str(e), "error")
    return redirect(url_for("web.board", q=request.form.get("full_name", "")))


@bp.post("/checkin")
def check_in():
    try:
        svc.check_in(int(request.form["visitor_id"]), int(request.form["station_id"]),
                     request.form.get("purpose") or None)
        flash("Checked in.", "ok")
    except (svc.HubError, KeyError, ValueError) as e:
        flash(str(e) if isinstance(e, svc.HubError) else "Pick a visitor and a station.", "error")
    return redirect(url_for("web.board"))


@bp.post("/checkout/<int:station_id>")
def check_out(station_id: int):
    session = svc.open_session_for_station(station_id)
    if session is None:
        flash("That station has no open session.", "error")
    else:
        result = svc.check_out(session["id"])
        flash(f"Checked out after {result['minutes']} min.", "ok")
    return redirect(url_for("web.board"))
