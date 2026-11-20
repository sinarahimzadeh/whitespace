import json
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .scheduler import schedule
from .schemas import SchedulePreviewRequest, ScheduleRequest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DIST = ROOT / "frontend" / "dist"

app = FastAPI()
REVIEW_LOCKS = {path.stem: Lock() for path in (DATA / "plans").glob("*.md")}


def plan_paths(plan_id):
    if plan_id not in REVIEW_LOCKS:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return DATA / "plans" / f"{plan_id}.md", DATA / "reviews" / f"{plan_id}.json"


def plan_response(plan_id, text, review):
    from .review import validate_review

    try:
        review = validate_review(review, text)
        result = schedule(review["tasks"], review["deadline_day"])
    except (ValidationError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=422, detail="This review cannot be scheduled. Run a new AI review.") from error
    return {"id": plan_id, "text": text, "review": review, "schedule": result}


@app.get("/api/plans")
def list_plans():
    plans = []
    for path in sorted((DATA / "plans").glob("*.md"), reverse=True):
        title = next((line.lstrip("# ").strip() for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("#")), path.stem)
        plans.append({"id": path.stem, "title": title})
    return plans


@app.get("/api/plans/{plan_id}")
def get_plan(plan_id: str):
    plan_path, review_path = plan_paths(plan_id)
    try:
        text = plan_path.read_text(encoding="utf-8")
        review = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=500, detail="The saved plan or review could not be loaded.") from error
    return plan_response(plan_id, text, review)


@app.post("/api/plans/{plan_id}/review")
def run_review(plan_id: str):
    from .review import ReviewValidationError, review_plan

    plan_path, review_path = plan_paths(plan_id)
    lock = REVIEW_LOCKS[plan_id]
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="An AI review is already running for this plan.")
    try:
        text = plan_path.read_text(encoding="utf-8")
        try:
            review = review_plan(text)
        except ReviewValidationError as error:
            raise HTTPException(status_code=502, detail="The AI review failed its source and format checks. The previous review has been kept.") from error
        except ValueError as error:
            raise HTTPException(status_code=503, detail="Check the AI provider, model and API key in .env.") from error
        except Exception as error:
            raise HTTPException(status_code=502, detail="The AI review failed. Check your API key, model and account credit, then try again.") from error
        response = plan_response(plan_id, text, review)
        temporary = review_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(review_path)
        return response
    finally:
        lock.release()


@app.post("/api/schedule")
def post_schedule(body: ScheduleRequest):
    return schedule([task.model_dump() for task in body.tasks], body.deadline_day)


@app.post("/api/plans/{plan_id}/preview")
def preview_corrections(plan_id: str, body: SchedulePreviewRequest):
    plan_paths(plan_id)
    return schedule([task.model_dump() for task in body.tasks], body.deadline_day)


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True))
