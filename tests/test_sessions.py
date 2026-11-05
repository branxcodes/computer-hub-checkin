def check_in(client, visitor=1, station=1, purpose="job search"):
    return client.post("/api/sessions", json={"visitor_id": visitor, "station_id": station, "purpose": purpose})


def test_health(client):
    assert client.get("/api/health").json == {"status": "ok"}


def test_check_in_marks_station_in_use(client):
    assert check_in(client).status_code == 201
    board = {s["label"]: s for s in client.get("/api/stations").json}
    assert board["PC-01"]["status"] == "in_use"
    assert board["PC-01"]["visitor"] == "Amina Nakato"
    assert board["PC-02"]["status"] == "free"


def test_station_cannot_be_double_booked(client):
    check_in(client, visitor=1, station=1)
    r = check_in(client, visitor=2, station=1)
    assert r.status_code == 409


def test_visitor_cannot_hold_two_stations(client):
    check_in(client, visitor=1, station=1)
    assert check_in(client, visitor=1, station=2).status_code == 409


def test_checkout_reports_minutes(client, clock):
    sid = check_in(client).json["id"]
    clock.advance(minutes=47)
    r = client.post(f"/api/sessions/{sid}/checkout")
    assert r.json["minutes"] == 47
    assert client.post(f"/api/sessions/{sid}/checkout").status_code == 409


def test_station_free_again_after_checkout(client):
    sid = check_in(client).json["id"]
    client.post(f"/api/sessions/{sid}/checkout")
    assert check_in(client, visitor=2, station=1).status_code == 201


def test_unknown_ids_return_404(client):
    assert check_in(client, visitor=99).status_code == 404
    assert check_in(client, station=99).status_code == 404
    assert client.post("/api/sessions/99/checkout").status_code == 404


def test_missing_fields_return_400(client):
    assert client.post("/api/sessions", json={"visitor_id": 1}).status_code == 400
