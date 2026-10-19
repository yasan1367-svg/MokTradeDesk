"""تست‌های بازه‌های زمانی پورصمدی (فاز TA-1)."""


def _seed_status(client):
    return client.get("/api/analytics/intervals/seed-status").json()


def test_seed_poursamadi_creates_9_intervals(client, db_session):
    """Seed all — creates 9 intervals (3 per symbol)."""
    resp = client.post("/api/analytics/intervals/seed-poursamadi")
    assert resp.status_code == 200

    status = _seed_status(client)
    assert status["poursamadi_seeded"] is True
    assert status["total_intervals"] == 9
    assert status["by_symbol"].get("XAUUSD") == 3
    assert status["by_symbol"].get("DJIUSD") == 3
    assert status["by_symbol"].get("EURUSD") == 3


def test_seed_poursamadi_is_idempotent(client, db_session):
    """Running seed-poursamadi twice must not duplicate intervals."""
    r1 = client.post("/api/analytics/intervals/seed-poursamadi")
    created1 = len(r1.json()["created"])

    r2 = client.post("/api/analytics/intervals/seed-poursamadi")
    created2 = len(r2.json()["created"])

    assert created1 == 9, f"First run should create 9, got {created1}"
    assert created2 == 0, f"Second run should create 0, got {created2}"

    status = _seed_status(client)
    assert status["total_intervals"] == 9


def test_seed_gold_windows_match_poursamadi(client, db_session):
    """Gold intervals must match Poursamadi's windows."""
    client.post("/api/analytics/intervals/seed-poursamadi")
    resp = client.get("/api/analytics/intervals/").json()

    gold = [i for i in resp if i["symbol"] == "XAUUSD"]
    assert len(gold) == 3
    gold.sort(key=lambda x: (x["start_hour"], x["start_minute"]))

    # A1: 10:30-13:30
    assert gold[0]["start_hour"] == 10
    assert gold[0]["start_minute"] == 30
    assert gold[0]["end_hour"] == 13
    assert gold[0]["end_minute"] == 30
    assert gold[0]["label"] == "A"
    assert gold[0]["priority"] == 1
    # A2: 16:00-17:00
    assert gold[1]["start_hour"] == 16
    assert gold[1]["start_minute"] == 0
    assert gold[1]["end_hour"] == 17
    assert gold[1]["end_minute"] == 0
    assert gold[1]["label"] == "A"
    # A3: 17:00-18:30
    assert gold[2]["start_hour"] == 17
    assert gold[2]["start_minute"] == 0
    assert gold[2]["end_hour"] == 18
    assert gold[2]["end_minute"] == 30
    assert gold[2]["label"] == "A"


def test_seed_dji_windows_match_poursamadi(client, db_session):
    """DJI intervals must match Poursamadi's windows."""
    client.post("/api/analytics/intervals/seed-poursamadi")
    resp = client.get("/api/analytics/intervals/").json()

    dji = [i for i in resp if i["symbol"] == "DJIUSD"]
    assert len(dji) == 3
    dji.sort(key=lambda x: (x["start_hour"], x["start_minute"]))

    assert dji[0]["start_hour"] == 17 and dji[0]["start_minute"] == 0
    assert dji[0]["end_hour"] == 18 and dji[0]["end_minute"] == 30
    assert dji[0]["label"] == "A" and dji[0]["priority"] == 1

    assert dji[1]["start_hour"] == 18 and dji[1]["start_minute"] == 30
    assert dji[1]["end_hour"] == 21 and dji[1]["end_minute"] == 30
    assert dji[1]["label"] == "B" and dji[1]["priority"] == 2

    assert dji[2]["start_hour"] == 21 and dji[2]["start_minute"] == 30
    assert dji[2]["end_hour"] == 23 and dji[2]["end_minute"] == 30
    assert dji[2]["label"] == "C" and dji[2]["priority"] == 3


def test_seed_status_before_seeding(client, db_session):
    """Before seeding, seed-status must report not seeded."""
    status = _seed_status(client)
    assert status["poursamadi_seeded"] is False
    assert status["total_intervals"] == 0


def test_individual_seed_gold_creates_3(client, db_session):
    """POST /intervals/seed-gold creates 3 gold intervals."""
    resp = client.post("/api/analytics/intervals/seed-gold")
    assert resp.status_code == 200
    assert len(resp.json()["created"]) == 3


def test_individual_seed_dji_creates_3(client, db_session):
    """POST /intervals/seed-dji creates 3 DJI intervals."""
    resp = client.post("/api/analytics/intervals/seed-dji")
    assert resp.status_code == 200
    assert len(resp.json()["created"]) == 3


def test_idempotent_by_name_and_symbol(client, db_session):
    """Same name+symbol must skip on re-run."""
    client.post("/api/analytics/intervals/seed-poursamadi")
    r2 = client.post("/api/analytics/intervals/seed-poursamadi")
    assert len(r2.json()["created"]) == 0