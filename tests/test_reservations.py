def reserve(client, visitor, station, start, end):
    return client.post("/api/reservations", json={
        "visitor_id": visitor, "station_id": station, "starts_at": start, "ends_at": end})


def test_reserve_and_detect_overlap(client):
    assert reserve(client, 1, 1, "2026-11-05T10:00", "2026-11-05T11:00").status_code == 201
    # overlaps the end of the first booking
    assert reserve(client, 2, 1, "2026-11-05T10:30", "2026-11-05T11:30").status_code == 409
    # back-to-back is fine
    assert reserve(client, 2, 1, "2026-11-05T11:00", "2026-11-05T12:00").status_code == 201
    # another station is fine
    assert reserve(client, 2, 2, "2026-11-05T10:30", "2026-11-05T11:30").status_code == 201


def test_reservation_rules(client):
    assert reserve(client, 1, 1, "2026-11-05T10:00", "2026-11-05T09:00").status_code == 400
    assert reserve(client, 1, 1, "2026-11-05T10:00", "2026-11-05T14:00").status_code == 400  # > 3h
    assert reserve(client, 1, 1, "2026-11-04T10:00", "2026-11-04T11:00").status_code == 400  # past
    assert reserve(client, 1, 1, "not-a-date", "2026-11-05T11:00").status_code == 400


def test_reserved_station_blocks_others_until_no_show_grace(client, clock):
    reserve(client, 1, 1, "2026-11-05T09:00", "2026-11-05T10:00")
    clock.advance(minutes=5)
    blocked = client.post("/api/sessions", json={"visitor_id": 2, "station_id": 1})
    assert blocked.status_code == 409
    clock.advance(minutes=20)  # 25 min after start: past the 15-minute grace
    released = client.post("/api/sessions", json={"visitor_id": 2, "station_id": 1})
    assert released.status_code == 201


def test_owner_can_check_into_reserved_station(client, clock):
    reserve(client, 1, 1, "2026-11-05T09:00", "2026-11-05T10:00")
    clock.advance(minutes=2)
    assert client.post("/api/sessions", json={"visitor_id": 1, "station_id": 1}).status_code == 201


def test_cancelled_reservation_frees_slot(client):
    rid = reserve(client, 1, 1, "2026-11-05T10:00", "2026-11-05T11:00").json["id"]
    assert client.delete(f"/api/reservations/{rid}").status_code == 204
    assert reserve(client, 2, 1, "2026-11-05T10:00", "2026-11-05T11:00").status_code == 201
