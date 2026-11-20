"""Route and SQLite behavior for isolated studio instances."""

import os
import sqlite3
import tempfile
from contextlib import closing
from datetime import date, timedelta

import pytest

from app import create_app


@pytest.fixture
def client():
    """Give each test an absent database path so startup creates the schema."""
    db_descriptor, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_descriptor)
    os.unlink(db_path)

    app = create_app({"TESTING": True, "DATABASE": db_path})
    try:
        with app.test_client() as test_client:
            yield test_client
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_landing_and_seeded_login(client):
    landing_response = client.get("/")
    assert landing_response.status_code == 200
    assert b"Repertoire Studio" in landing_response.data

    login_response = client.post(
        "/login",
        data={"username": "maowen", "password": "piano2026"},
        follow_redirects=True,
    )
    assert login_response.status_code == 200
    assert b"Heroic Polonaise" in login_response.data


def test_registration_and_duplicate_rejection(client):
    registration_response = client.post(
        "/register",
        data={
            "username": "chopin_student",
            "password": "secretpassword",
            "confirmation": "secretpassword",
        },
        follow_redirects=True,
    )
    assert registration_response.status_code == 200
    assert b"chopin_student" in registration_response.data

    client.get("/logout")
    duplicate_response = client.post(
        "/register",
        data={
            "username": "chopin_student",
            "password": "anotherpassword",
            "confirmation": "anotherpassword",
        },
        follow_redirects=True,
    )
    assert b"already taken" in duplicate_response.data


def test_add_piece_and_log_practice_flow(client):
    client.post(
        "/login",
        data={"username": "maowen", "password": "piano2026"},
        follow_redirects=True,
    )

    add_piece_response = client.post(
        "/repertoire/add",
        data={
            "title": "Ballade No. 1 in G Minor",
            "composer": "Frederic Chopin",
            "opus_catalog": "Op. 23",
            "musical_key": "G Minor",
            "musical_form": "Modified Sonata Form",
            "technical_focus": "Presto con fuoco coda octaves",
            "difficulty": "5",
            "mastery_status": "In Progress",
            "notes": "Pacing the Largo introduction.",
        },
        follow_redirects=True,
    )
    assert add_piece_response.status_code == 200
    assert b"Ballade No. 1 in G Minor" in add_piece_response.data

    with closing(sqlite3.connect(client.application.config["DATABASE"])) as db:
        piece_id = db.execute(
            "SELECT id FROM pieces WHERE title = ?", ("Ballade No. 1 in G Minor",)
        ).fetchone()[0]
    before_logging = client.get("/api/analytics-data").get_json()
    practice_date = date.today().isoformat()

    log_response = client.post(
        "/practice/log",
        data={
            "piece_id": str(piece_id),
            "duration_minutes": "50",
            "target_bpm": "120",
            "measure_range": "mm. 1-40",
            "practiced_on": practice_date,
            "session_notes": "Focused on left-hand accompaniment balance.",
        },
        follow_redirects=True,
    )
    assert log_response.status_code == 200
    assert b"Practice session logged" in log_response.data

    analytics_response = client.get("/api/analytics-data")
    assert analytics_response.status_code == 200
    payload = analytics_response.get_json()
    assert payload.keys() == {"composers", "daily", "forms"}
    composer = "Frederic Chopin"
    prior_composer_totals = {row["composer"]: row["minutes"] for row in before_logging["composers"]}
    composer_totals = {row["composer"]: row["minutes"] for row in payload["composers"]}
    prior_daily_totals = {row["practiced_on"]: row["minutes"] for row in before_logging["daily"]}
    daily_totals = {row["practiced_on"]: row["minutes"] for row in payload["daily"]}
    assert composer_totals[composer] == prior_composer_totals[composer] + 50
    assert daily_totals[practice_date] == prior_daily_totals[practice_date] + 50


def test_guest_route_and_analytics_redirects(client):
    for path in ("/repertoire", "/repertoire/add", "/analytics", "/api/analytics-data"):
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"] == "/login"


def test_other_account_cannot_change_or_log_practice_on_a_seed_piece(client):
    with closing(sqlite3.connect(client.application.config["DATABASE"])) as db:
        piece_id, initial_status = db.execute(
            "SELECT id, mastery_status FROM pieces WHERE title LIKE ?", ("Heroic Polonaise%",)
        ).fetchone()
        initial_log_count = db.execute("SELECT COUNT(*) FROM practice_logs").fetchone()[0]

    client.post("/register", data={
        "username": "second_studio", "password": "local-test-pass", "confirmation": "local-test-pass",
    })
    assert b"Heroic Polonaise" not in client.get("/repertoire").data
    assert client.get("/api/analytics-data").get_json() == {"composers": [], "daily": [], "forms": []}
    client.post(f"/repertoire/{piece_id}/status", data={"mastery_status": "In Progress"})
    client.post(f"/repertoire/{piece_id}/delete")
    client.post("/practice/log", data={"piece_id": piece_id, "duration_minutes": 30, "target_bpm": 80})

    with closing(sqlite3.connect(client.application.config["DATABASE"])) as db:
        assert db.execute("SELECT mastery_status FROM pieces WHERE id = ?", (piece_id,)).fetchone() == (initial_status,)
        assert db.execute("SELECT COUNT(*) FROM practice_logs").fetchone() == (initial_log_count,)


def test_piece_delete_cascades_to_its_practice_logs(client):
    client.post("/login", data={"username": "maowen", "password": "piano2026"})
    with closing(sqlite3.connect(client.application.config["DATABASE"])) as db:
        piece_id, linked_count = db.execute(
            "SELECT piece_id, COUNT(*) FROM practice_logs GROUP BY piece_id ORDER BY piece_id LIMIT 1"
        ).fetchone()
    assert linked_count > 0

    assert client.post(f"/repertoire/{piece_id}/delete").status_code == 302
    with closing(sqlite3.connect(client.application.config["DATABASE"])) as db:
        assert db.execute("SELECT id FROM pieces WHERE id = ?", (piece_id,)).fetchone() is None
        assert db.execute("SELECT COUNT(*) FROM practice_logs WHERE piece_id = ?", (piece_id,)).fetchone() == (0,)


def test_daily_series_preserves_observed_day_limit_and_order(client):
    client.post("/login", data={"username": "maowen", "password": "piano2026"})
    with closing(sqlite3.connect(client.application.config["DATABASE"])) as db:
        piece_id = db.execute("SELECT id FROM pieces ORDER BY id LIMIT 1").fetchone()[0]
    for days_before in range(7, 20):
        client.post("/practice/log", data={
            "piece_id": piece_id, "duration_minutes": 12, "target_bpm": 90,
            "practiced_on": (date.today() - timedelta(days=days_before)).isoformat(),
        })

    payload = client.get("/api/analytics-data").get_json()
    days = [row["practiced_on"] for row in payload["daily"]]
    assert len(days) == 14
    assert days == sorted(days)
    assert date.today().isoformat() not in days


def test_synthetic_demo_has_its_own_account_and_database(tmp_path, monkeypatch):
    demo_db = tmp_path / "synthetic.db"
    monkeypatch.setenv("REPERTOIRE_DEMO_DATABASE", str(demo_db))
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-only-key")
    demo_app = create_app({"TESTING": True})
    demo_client = demo_app.test_client()
    assert b"studio-demo" in demo_client.get("/login").data
    assert b"maowen" not in demo_client.get("/login").data
    demo_client.post("/login", data={"username": "studio-demo", "password": "demo-only"})

    response = demo_client.get("/api/analytics-data")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload.keys() == {"composers", "daily", "forms"}
    assert sum(row["minutes"] for row in payload["daily"]) == 170
    assert len(payload["daily"]) == 7
    assert sum(row["count"] for row in payload["forms"]) == 5
    assert any(row["minutes"] == 0 for row in payload["composers"])
