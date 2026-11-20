from collections import defaultdict

from ortools.sat.python import cp_model

from .schemas import TaskList


def _dependency_order(by_id):
    """Return dependency-first order, or the ids on an actual cycle."""
    state, stack, order = {}, [], []

    def visit(task_id):
        if state.get(task_id) == 1:
            return stack[stack.index(task_id):]
        if state.get(task_id) == 2:
            return []
        state[task_id] = 1
        stack.append(task_id)
        for dependency in by_id[task_id]["depends_on"]:
            cycle = visit(dependency)
            if cycle:
                return cycle
        stack.pop()
        state[task_id] = 2
        order.append(task_id)
        return []

    for task_id in by_id:
        cycle = visit(task_id)
        if cycle:
            return [], cycle
    return order, []


def schedule(tasks, deadline_day):
    tasks = TaskList(tasks=tasks).model_dump()["tasks"]
    if deadline_day is not None and type(deadline_day) is not int:
        raise ValueError("deadline_day must be an integer or null.")
    by_id = {task["id"]: task for task in tasks}
    order, cycle = _dependency_order(by_id)
    if cycle:
        return {"status": "cycle", "schedule": [], "end_day": None,
                "deadline_day": deadline_day, "meets_deadline": None,
                "days_late": None, "cycle": cycle,
                "optimal": False, "lower_bound_day": None}

    # Both the longest dependency chain and each person's total work are
    # lower bounds: no valid schedule can finish earlier than either.
    earliest_end, owner_days = {}, defaultdict(int)
    for task_id in order:
        task = by_id[task_id]
        earliest_end[task_id] = task["duration_days"] + max(
            (earliest_end[dep] for dep in task["depends_on"]), default=0)
        if task["owner"] is not None:
            owner_days[task["owner"]] += task["duration_days"]
    lower_bound = max([0, *earliest_end.values(), *owner_days.values()])

    # A valid fallback and a complete starting solution for the optimiser.
    # People are available only after their previous job finishes.
    owner_end, greedy = {}, {}
    for task_id in order:
        task = by_id[task_id]
        start = max((greedy[dep][1] for dep in task["depends_on"]), default=0)
        if task["owner"] is not None:
            start = max(start, owner_end.get(task["owner"], 0))
        end = start + task["duration_days"]
        greedy[task_id] = (start, end)
        if task["owner"] is not None:
            owner_end[task["owner"]] = end
    horizon = max((end for _, end in greedy.values()), default=0)
    timings, optimal = greedy, horizon == lower_bound

    # Keep a valid answer if the time limit is reached. Extremely large Python
    # integers stay on the fallback path, outside CP-SAT's integer range.
    if tasks and not optimal and sum(task["duration_days"] for task in tasks) < 2**60:
        model = cp_model.CpModel()
        starts, ends, people = {}, {}, defaultdict(list)
        for task in tasks:
            task_id = task["id"]
            starts[task_id] = model.new_int_var(0, horizon, f"start_{task_id}")
            ends[task_id] = model.new_int_var(0, horizon, f"end_{task_id}")
            interval = model.new_interval_var(starts[task_id], task["duration_days"],
                                              ends[task_id], f"task_{task_id}")
            if task["owner"] is not None:
                people[task["owner"]].append(interval)
            model.add_hint(starts[task_id], greedy[task_id][0])
            model.add_hint(ends[task_id], greedy[task_id][1])
        for task in tasks:
            for dependency in task["depends_on"]:
                model.add(starts[task["id"]] >= ends[dependency])
        for intervals in people.values():
            model.add_no_overlap(intervals)
        finish = model.new_int_var(lower_bound, horizon, "finish")
        model.add_max_equality(finish, list(ends.values()))
        model.add_hint(finish, horizon)
        model.minimize(finish)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 6
        solver.parameters.num_search_workers = 4
        solver.parameters.random_seed = 0
        status = solver.solve(model)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            timings = {task_id: (solver.value(starts[task_id]), solver.value(ends[task_id]))
                       for task_id in by_id}
            optimal = status == cp_model.OPTIMAL

    items = [{"id": task["id"], "start_day": timings[task["id"]][0],
              "end_day": timings[task["id"]][1]} for task in tasks]
    end_day = max((item["end_day"] for item in items), default=0)
    return {"status": "scheduled", "schedule": items, "end_day": end_day,
            "deadline_day": deadline_day,
            "meets_deadline": end_day <= deadline_day if deadline_day is not None else None,
            "days_late": max(0, end_day - deadline_day) if deadline_day is not None else None,
            "cycle": [], "optimal": optimal,
            "lower_bound_day": end_day if optimal else lower_bound}
