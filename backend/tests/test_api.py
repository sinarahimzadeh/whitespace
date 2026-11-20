import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402


def test_plans_are_listed():
    response = TestClient(app).get("/api/plans")
    assert response.status_code == 200
    assert {plan["id"] for plan in response.json()} == {"spring-market", "lantern-festival", "harbour-run"}


def test_unknown_plan_is_a_json_404():
    response = TestClient(app).get("/api/plans/not-a-plan")
    assert response.status_code == 404
    assert response.json()["detail"] == "Plan not found."


def test_all_three_plans_load_including_harbour_cycle():
    client = TestClient(app)
    for plan_id in ("spring-market", "lantern-festival", "harbour-run"):
        response = client.get(f"/api/plans/{plan_id}")
        assert response.status_code == 200
        assert response.json()["text"].startswith("# Pellerby")
    assert client.get("/api/plans/harbour-run").json()["schedule"]["status"] == "cycle"
    assert client.get("/api/plans/harbour-run").json()["review"]["deadline_day"] is None
    spring = client.get("/api/plans/spring-market").json()["schedule"]
    assert (spring["end_day"], spring["deadline_day"]) == (18, 21)
    lantern = client.get("/api/plans/lantern-festival").json()["schedule"]
    assert (lantern["end_day"], lantern["deadline_day"], lantern["days_late"]) == (52, 45, 7)


VALID_TASK = {"id": "A", "name": "Book the hall", "owner": "Ann", "duration_days": 1, "depends_on": []}


@pytest.mark.parametrize("body", [
    {},
    {"tasks": [VALID_TASK, VALID_TASK], "deadline_day": 10},
    {"tasks": [{**VALID_TASK, "duration_days": 0}], "deadline_day": 10},
    {"tasks": [{**VALID_TASK, "duration_days": True}], "deadline_day": 10},
    {"tasks": [{**VALID_TASK, "duration_days": "2"}], "deadline_day": 10},
    {"tasks": [{**VALID_TASK, "depends_on": ["missing"]}], "deadline_day": 10},
    {"tasks": [{**VALID_TASK, "id": str(i)} for i in range(61)], "deadline_day": 10},
    {"tasks": [], "deadline_day": None},
])
def test_invalid_schedule_input_is_rejected_as_json(body):
    response = TestClient(app).post("/api/schedule", json=body)
    assert 400 <= response.status_code < 500
    assert "detail" in response.json()


def test_review_button_saves_and_displays_new_result(monkeypatch, tmp_path):
    import json
    import app.main as main
    import app.review as reviewer

    (tmp_path / "plans").mkdir()
    (tmp_path / "reviews").mkdir()
    text = "# Test plan\nAnn books the hall in one day."
    (tmp_path / "plans" / "spring-market.md").write_text(text, encoding="utf-8")
    review = {"deadline_day": 10, "tasks": [{**VALID_TASK, "quote": "Ann books the hall in one day."}], "findings": []}
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(reviewer, "review_plan", lambda source: review if source == text else None)
    client = TestClient(app)
    response = client.post("/api/plans/spring-market/review")
    assert response.status_code == 200
    assert response.json()["review"] == review
    assert response.json()["schedule"]["end_day"] == 1
    assert client.get("/api/plans/spring-market").json() == response.json()
    assert json.loads((tmp_path / "reviews" / "spring-market.json").read_text(encoding="utf-8")) == review


def test_failed_ai_call_keeps_previous_review(monkeypatch, tmp_path):
    import app.main as main
    import app.review as reviewer

    (tmp_path / "plans").mkdir()
    (tmp_path / "reviews").mkdir()
    (tmp_path / "plans" / "spring-market.md").write_text("# Plan", encoding="utf-8")
    saved = tmp_path / "reviews" / "spring-market.json"
    saved.write_text('{"original": true}', encoding="utf-8")
    monkeypatch.setattr(main, "DATA", tmp_path)
    def fail(_):
        raise RuntimeError("Provider unavailable")
    monkeypatch.setattr(reviewer, "review_plan", fail)
    response = TestClient(app).post("/api/plans/spring-market/review")
    assert response.status_code == 502
    assert saved.read_text(encoding="utf-8") == '{"original": true}'


def test_corrections_recalculate_without_changing_saved_ai_review():
    import app.main as main

    client = TestClient(app)
    path = main.DATA / "reviews" / "spring-market.json"
    original = path.read_text(encoding="utf-8")
    review = client.get("/api/plans/spring-market").json()["review"]
    review["tasks"][0]["duration_days"] += 2
    result = client.post("/api/plans/spring-market/preview", json=review)
    assert result.status_code == 200
    assert result.json()["end_day"] == 20
    assert path.read_text(encoding="utf-8") == original


def test_corrections_can_resolve_a_cycle_and_leave_deadline_unknown():
    client = TestClient(app)
    review = client.get("/api/plans/harbour-run").json()["review"]
    for task in review["tasks"]:
        if task["name"] == "Take out the event insurance":
            task["depends_on"] = []
    result = client.post("/api/plans/harbour-run/preview", json=review)
    assert result.status_code == 200
    assert result.json()["status"] == "scheduled"
    assert result.json()["cycle"] == []
    assert result.json()["meets_deadline"] is None
