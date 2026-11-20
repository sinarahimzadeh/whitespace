from collections import defaultdict
from itertools import permutations, product
from pathlib import Path
import random
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.scheduler import schedule
from check_contract import validate_schedule_response


def task(task_id, duration, owner=None, dependencies=()):
    return {"id": task_id, "name": task_id, "owner": owner,
            "duration_days": duration, "depends_on": list(dependencies)}


def brute_force_finish(tasks):
    """Independent oracle: enumerate every possible order of each person's work."""
    owners = defaultdict(list)
    for item in tasks:
        if item["owner"] is not None:
            owners[item["owner"]].append(item["id"])
    best = sum(item["duration_days"] for item in tasks)
    for orders in product(*(permutations(ids) for ids in owners.values())):
        dependencies = {item["id"]: set(item["depends_on"]) for item in tasks}
        for order in orders:
            for previous, following in zip(order, order[1:]):
                dependencies[following].add(previous)
        ends = {}
        while len(ends) < len(tasks):
            ready = [item for item in tasks if item["id"] not in ends
                     and dependencies[item["id"]].issubset(ends)]
            if not ready:
                break
            for item in ready:
                ends[item["id"]] = item["duration_days"] + max(
                    (ends[dep] for dep in dependencies[item["id"]]), default=0)
        if len(ends) == len(tasks):
            best = min(best, max(ends.values(), default=0))
    return best


def test_optimiser_matches_exhaustive_small_instances():
    rng = random.Random(7)
    for _ in range(20):
        tasks = [task(str(i), rng.randint(1, 5), rng.choice(["Ann", "Bob", None]),
                      [str(j) for j in range(i) if rng.random() < .25]) for i in range(6)]
        result = schedule(tasks, 20)
        assert validate_schedule_response({"tasks": tasks, "deadline_day": 20}, result) == []
        assert result["end_day"] == brute_force_finish(tasks)
        assert result["optimal"] is True


def test_cycle_names_only_tasks_in_the_circle():
    tasks = [task("A", 1, dependencies=["B"]), task("B", 1, dependencies=["A"]),
             task("downstream", 1, dependencies=["A"])]
    result = schedule(tasks, 10)
    assert result["status"] == "cycle"
    assert set(result["cycle"]) == {"A", "B"}
    assert validate_schedule_response({"tasks": tasks, "deadline_day": 10}, result) == []


def test_self_cycle():
    result = schedule([task("A", 1, dependencies=["A"])], 10)
    assert result["cycle"] == ["A"]


def test_unknown_deadline_still_produces_a_schedule():
    result = schedule([task("A", 3)], None)
    assert result["end_day"] == 3
    assert result["deadline_day"] is None
    assert result["meets_deadline"] is None
    assert result["days_late"] is None


def test_empty_schedule_and_negative_deadline():
    request = {"tasks": [], "deadline_day": -2}
    result = schedule([], -2)
    assert validate_schedule_response(request, result) == []


def test_null_owners_can_work_in_parallel():
    result = schedule([task("A", 3), task("B", 4)], 10)
    assert result["end_day"] == 4


def test_sixty_tasks_within_contract_time_limit():
    tasks = [task(str(i), i % 5 + 1, f"Person {i % 6}",
                  [str(i - 7)] if i >= 7 else []) for i in range(60)]
    started = time.monotonic()
    result = schedule(tasks, 100)
    assert time.monotonic() - started < 10
    assert validate_schedule_response({"tasks": tasks, "deadline_day": 100}, result) == []


def test_large_integer_durations_remain_valid():
    tasks = [task("A", 2**70, "Ann"), task("B", 2**70, "Ann")]
    result = schedule(tasks, 2**72)
    assert validate_schedule_response({"tasks": tasks, "deadline_day": 2**72}, result) == []
