"""Tests for Forex Factory news parsing, storage, scheduling, and API behavior."""
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest

from app.api.news import news_now
from app.main import app
from app.models.economic_event import EconomicEvent
from app.services.news_service import (
    _upsert_events,
    ensure_today_events,
    fetch_forex_factory,
    get_upcoming,
    reset_fetch_state,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ff_current_week.json"
FIXTURE_JSON = FIXTURE_PATH.read_text(encoding="utf-8")
MOCK_FIXTURE_RESPONSE = (200, FIXTURE_JSON, None)
TEHRAN = ZoneInfo("Asia/Tehran")


@pytest.fixture(autouse=True)
def _isolated_fetch_state():
    reset_fetch_state()
    yield
    reset_fetch_state()


def _event(title="FOMC Meeting Minutes", forecast="1.0%", event_time=None):
    return {
        "title": title,
        "currency": "USD",
        "impact": "High",
        "event_time": event_time or datetime(2026, 10, 7, 18, tzinfo=timezone.utc),
        "forecast": forecast,
        "previous": "0.5%",
    }


def _today_response(client, now, events, query="scope=today&limit=20"):
    app.dependency_overrides[news_now] = lambda: now
    try:
        with patch("app.services.news_service.fetch_forex_factory", return_value=events):
            return client.get(f"/api/news/upcoming?{query}")
    finally:
        app.dependency_overrides.pop(news_now, None)


def test_scope_today_excludes_tomorrow_tehran(client):
    now = datetime(2026, 10, 7, 10, 0, tzinfo=timezone.utc)
    events = [
        _event("President Trump Speaks", event_time=datetime(2026, 10, 7, 17, 0, tzinfo=timezone.utc)),
        _event("FOMC Meeting Minutes", event_time=datetime(2026, 10, 7, 18, 0, tzinfo=timezone.utc)),
        _event("FOMC Member Waller Speaks", event_time=datetime(2026, 10, 8, 8, 30, tzinfo=timezone.utc)),
    ]

    response = _today_response(client, now, events)

    assert response.status_code == 200
    assert [event["title"] for event in response.json()["events"]] == [
        "President Trump Speaks", "FOMC Meeting Minutes",
    ]


def test_scope_today_includes_event_from_last_hour(client):
    now = datetime(2026, 10, 7, 10, 0, tzinfo=timezone.utc)
    events = [
        _event("90 minutes ago", event_time=now - timedelta(minutes=90)),
        _event("30 minutes ago", event_time=now - timedelta(minutes=30)),
    ]

    response = _today_response(client, now, events)

    assert [event["title"] for event in response.json()["events"]] == ["30 minutes ago"]
    assert response.json()["events"][0]["minutes_until"] == -30


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 10, 7, 20, 29, tzinfo=timezone.utc), ["Before midnight"]),
        (datetime(2026, 10, 7, 20, 31, tzinfo=timezone.utc), ["Before midnight", "After midnight"]),
    ],
)
def test_scope_today_day_boundary(client, now, expected):
    events = [
        _event("Before midnight", event_time=datetime(2026, 10, 7, 20, 20, tzinfo=timezone.utc)),
        _event("After midnight", event_time=datetime(2026, 10, 7, 20, 40, tzinfo=timezone.utc)),
    ]

    response = _today_response(client, now, events)

    assert [event["title"] for event in response.json()["events"]] == expected


def test_default_upcoming_unchanged(client):
    now = datetime(2026, 10, 7, 10, 0, tzinfo=timezone.utc)
    events = [
        _event("Past", event_time=now - timedelta(minutes=30)),
        _event("Tomorrow", event_time=now + timedelta(days=1)),
        _event("Within seven days", event_time=now + timedelta(days=6)),
        _event("Beyond seven days", event_time=now + timedelta(days=8)),
    ]

    response = _today_response(client, now, events, query="limit=20")

    assert [event["title"] for event in response.json()["events"]] == [
        "Tomorrow", "Within seven days",
    ]


def test_limit_20_accepted(client):
    now = datetime(2026, 10, 7, 10, 0, tzinfo=timezone.utc)
    events = [
        _event(f"Event {index}", event_time=now + timedelta(minutes=index + 1))
        for index in range(20)
    ]

    response = _today_response(client, now, events)

    assert response.status_code == 200
    assert len(response.json()["events"]) == 20


@patch("app.services.news_service._http_get")
def test_parse_json_iso_with_offset_ny(mock_get):
    payload = [{
        "title": "FOMC Meeting Minutes",
        "country": "USD",
        "date": "2026-10-07T14:00:00-04:00",
        "impact": "High",
        "forecast": "",
        "previous": "",
    }]
    mock_get.return_value = (200, json.dumps(payload), None)

    events = fetch_forex_factory()

    assert events[0]["event_time"].isoformat() == "2026-10-07T18:00:00+00:00"


@patch("app.services.news_service._http_get", return_value=MOCK_FIXTURE_RESPONSE)
def test_filter_usd_high_and_medium(_mock_get):
    events = fetch_forex_factory()

    assert events
    assert {event["currency"] for event in events} == {"USD"}
    assert {event["impact"] for event in events} <= {"High", "Medium"}
    assert not any("OPEC" in event["title"] for event in events)


@patch("app.services.news_service._http_get")
def test_parser_skips_invalid_and_duplicate_items(mock_get):
    valid = {
        "title": "Fed Chair Speaks", "country": "USD", "impact": "Medium",
        "date": "2026-10-07T14:00:00-04:00", "forecast": "", "previous": "",
    }
    mock_get.return_value = (200, json.dumps([
        valid, valid.copy(), {**valid, "title": ""}, {**valid, "date": "bad"},
    ]), None)

    assert len(fetch_forex_factory()) == 1


def test_ny_2335_rolls_to_next_day_in_tehran():
    utc_time = datetime.fromisoformat("2026-10-07T23:35:00-04:00").astimezone(timezone.utc)

    assert utc_time.isoformat() == "2026-10-08T03:35:00+00:00"
    assert utc_time.astimezone(TEHRAN).strftime("%Y-%m-%d %H:%M") == "2026-10-08 07:05"


@patch("app.services.news_service.fetch_forex_factory")
def test_api_events_have_timezone_info(mock_fetch, client):
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_fetch.return_value = [_event(event_time=future)]

    response = client.get("/api/news/upcoming")

    assert response.status_code == 200
    for event in response.json()["events"]:
        value = event["event_time"]
        assert value.endswith("Z") or re.search(r"T.*[+-]\d{2}:\d{2}$", value)


@patch("app.services.news_service.fetch_forex_factory")
def test_api_events_survive_db_roundtrip(mock_fetch, client, db_session):
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_fetch.return_value = [_event(event_time=future)]

    ensure_today_events(db_session)
    db_session.expunge_all()
    response = client.get("/api/news/upcoming")

    assert response.json()["events"][0]["event_time"].endswith("+00:00")


def test_upsert_does_not_duplicate(db_session):
    fetched_date = date(2026, 10, 7)
    _upsert_events(db_session, [_event(forecast="1.0%")], fetched_date)
    db_session.commit()
    db_session.expunge_all()
    _upsert_events(db_session, [_event(forecast="2.0%")], fetched_date)
    db_session.commit()
    db_session.expunge_all()

    rows = db_session.query(EconomicEvent).all()
    assert len(rows) == 1
    assert rows[0].forecast == "2.0%"


@patch("app.services.news_service.fetch_forex_factory", side_effect=RuntimeError("offline"))
def test_failed_fetch_keeps_old_rows_and_marks_stale(_mock_fetch, client, db_session):
    db_session.add(EconomicEvent(
        title="Cached", currency="USD", impact="High",
        event_time=datetime.now(timezone.utc) + timedelta(hours=1),
        fetched_date=date(2026, 10, 6),
    ))
    db_session.commit()

    response = client.get("/api/news/upcoming")

    assert db_session.query(EconomicEvent).count() == 1
    assert response.json()["stale"] is True
    assert response.json()["events"][0]["title"] == "Cached"


def test_no_refetch_within_30_minutes_after_failure(db_session):
    fetch = Mock(side_effect=RuntimeError("offline"))
    now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    with patch("app.services.news_service.fetch_forex_factory", fetch):
        ensure_today_events(db_session, now=now)
        ensure_today_events(db_session, now=now + timedelta(minutes=29))

    assert fetch.call_count == 1


def test_ensure_today_events_fetches_once_per_tehran_day(db_session):
    fetch = Mock(return_value=[])
    before_midnight = datetime(2026, 10, 7, 20, 29, tzinfo=timezone.utc)
    after_midnight = datetime(2026, 10, 7, 20, 31, tzinfo=timezone.utc)
    with patch("app.services.news_service.fetch_forex_factory", fetch):
        ensure_today_events(db_session, now=before_midnight)
        ensure_today_events(db_session, now=after_midnight)

    assert fetch.call_count == 2


def test_quiet_week_does_not_refetch(db_session):
    fetch = Mock(return_value=[])
    now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    with patch("app.services.news_service.fetch_forex_factory", fetch):
        ensure_today_events(db_session, now=now)
        ensure_today_events(db_session, now=now + timedelta(hours=2))

    assert fetch.call_count == 1


def test_restart_uses_today_database_rows(db_session):
    now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    db_session.add(EconomicEvent(
        title="Existing", currency="USD", impact="High", event_time=now,
        fetched_date=now.astimezone(TEHRAN).date(),
    ))
    db_session.commit()
    fetch = Mock(return_value=[])

    with patch("app.services.news_service.fetch_forex_factory", fetch):
        ensure_today_events(db_session, now=now)

    fetch.assert_not_called()


def test_weekly_cleanup_only_after_success(db_session):
    now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    db_session.add(EconomicEvent(
        title="Old", currency="USD", impact="High",
        event_time=now - timedelta(days=8), fetched_date=date(2026, 9, 29),
    ))
    db_session.commit()

    with patch("app.services.news_service.fetch_forex_factory", side_effect=RuntimeError("offline")):
        ensure_today_events(db_session, now=now)

    assert db_session.query(EconomicEvent).count() == 1


def test_weekly_cleanup_after_success(db_session):
    now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    db_session.add(EconomicEvent(
        title="Old", currency="USD", impact="High",
        event_time=now - timedelta(days=8), fetched_date=date(2026, 9, 29),
    ))
    db_session.commit()

    with patch("app.services.news_service.fetch_forex_factory", return_value=[]):
        ensure_today_events(db_session, now=now)

    assert db_session.query(EconomicEvent).count() == 0


def test_get_upcoming_returns_sorted_events_within_seven_days(db_session):
    now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    for title, event_time in (
        ("Within 2 days", now + timedelta(days=2)),
        ("Past", now - timedelta(minutes=1)),
        ("Within 1 day", now + timedelta(days=1)),
        ("Beyond 7 days", now + timedelta(days=8)),
    ):
        db_session.add(EconomicEvent(
            title=title, currency="USD", impact="High",
            event_time=event_time, fetched_date=date(2026, 10, 7),
        ))
    db_session.commit()

    upcoming = get_upcoming(db_session, limit=4, now=now)

    assert [event.title for event in upcoming] == ["Within 1 day", "Within 2 days"]


@patch("app.services.news_service.fetch_forex_factory", return_value=[])
def test_refresh_endpoint_respects_attempt_throttle(mock_fetch, client):
    assert client.get("/api/news/refresh").status_code == 200
    assert client.get("/api/news/refresh").status_code == 200
    assert mock_fetch.call_count == 1