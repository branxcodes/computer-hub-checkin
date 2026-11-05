def test_register_and_search(client):
    r = client.post("/api/visitors", json={"full_name": "Grace Achieng", "email": "Grace@Example.org"})
    assert r.status_code == 201
    found = client.get("/api/visitors?q=grace").json
    assert [v["email"] for v in found] == ["grace@example.org"]  # email normalized


def test_duplicate_email_rejected(client):
    assert client.post("/api/visitors", json={"full_name": "X", "email": "amina@example.org"}).status_code == 409


def test_name_required(client):
    assert client.post("/api/visitors", json={"full_name": "  "}).status_code == 400


def test_daily_report(client, clock):
    a = client.post("/api/sessions", json={"visitor_id": 1, "station_id": 1, "purpose": "job search"}).json["id"]
    b = client.post("/api/sessions", json={"visitor_id": 2, "station_id": 2, "purpose": "schoolwork"}).json["id"]
    clock.advance(minutes=30)
    client.post(f"/api/sessions/{a}/checkout")
    clock.advance(minutes=30)
    client.post(f"/api/sessions/{b}/checkout")

    rep = client.get("/api/reports/daily?day=2026-11-05").json
    assert rep["sessions"] == 2
    assert rep["unique_visitors"] == 2
    assert rep["total_minutes"] == 90
    assert rep["average_minutes"] == 45
    assert rep["by_purpose"] == {"job search": 1, "schoolwork": 1}


def test_front_desk_page_flow(client):
    page = client.get("/")
    assert b"PC-01" in page.data
    r = client.post("/checkin", data={"visitor_id": 1, "station_id": 1, "purpose": "printing"},
                    follow_redirects=True)
    assert b"Checked in." in r.data
    r = client.post("/checkout/1", follow_redirects=True)
    assert b"Checked out" in r.data
