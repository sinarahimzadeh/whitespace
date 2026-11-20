from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.review import ReviewValidationError, review_plan, validate_review


def review(quote="Ann books the hall."):
    return {"deadline_day": None, "tasks": [{"id": "A", "name": "Book the hall",
        "owner": "Ann", "duration_days": 1, "depends_on": [], "quote": quote}],
        "findings": [{"title": "No deadline", "detail": "Confirm the target day.", "quote": None}]}


def test_quote_matching_normalises_whitespace_only():
    assert validate_review(review(), "Ann  books\nthe hall.") == review()
    with pytest.raises(ReviewValidationError):
        validate_review(review("ann books the hall."), "Ann books the hall.")


def test_separate_source_passages_cannot_be_joined_into_one_quote():
    with pytest.raises(ReviewValidationError):
        validate_review(review("Ann books the hall. Bob prints posters."),
                        "Ann books the hall. Other text. Bob prints posters.")


def test_unknown_dependency_is_rejected():
    output = review()
    output["tasks"][0]["depends_on"] = ["missing"]
    with pytest.raises(ReviewValidationError):
        validate_review(output, "Ann books the hall.")


def test_conflicting_deadline_evidence_overrides_model_guess():
    output = review()
    output["deadline_day"] = 42
    output["deadline_candidates"] = [
        {"day": 30, "quote": "The run is 30 days after kickoff."},
        {"day": 35, "quote": "Everything is due five weeks after kickoff."},
    ]
    source = "Ann books the hall. The run is 30 days after kickoff. Everything is due five weeks after kickoff."
    assert validate_review(output, source)["deadline_day"] is None


class ModelReplies:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return next(self.replies)


def test_invalid_quote_gets_one_repair_attempt():
    model = ModelReplies([review("Invented quote"), review()])
    assert review_plan("Ann books the hall.", model=model) == review()
    assert model.calls == 2


def test_repeated_invalid_answer_fails_instead_of_being_accepted():
    model = ModelReplies([review("Invented quote"), review("Still invented")])
    with pytest.raises(ReviewValidationError):
        review_plan("Ann books the hall.", model=model)
    assert model.calls == 2
