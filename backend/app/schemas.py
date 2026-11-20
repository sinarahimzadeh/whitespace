from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Task(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    name: str
    owner: str | None
    duration_days: Annotated[int, Field(ge=1)]
    depends_on: list[str]


class TaskList(BaseModel):
    model_config = ConfigDict(strict=True)

    tasks: Annotated[list[Task], Field(max_length=60)]

    @model_validator(mode="after")
    def check_references(self):
        ids = [task.id for task in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("Task ids must be unique.")
        known = set(ids)
        for task in self.tasks:
            for dependency in task.depends_on:
                if dependency not in known:
                    raise ValueError(f"Task {task.id} depends on unknown task {dependency}.")
        return self


class ScheduleRequest(TaskList):
    deadline_day: int


class SchedulePreviewRequest(TaskList):
    deadline_day: int | None


class ReviewTask(Task):
    quote: str


class ReviewFinding(BaseModel):
    model_config = ConfigDict(strict=True)

    title: str
    detail: str
    quote: str | None


class DeadlineCandidate(BaseModel):
    model_config = ConfigDict(strict=True)

    day: int
    quote: str


class ReviewData(TaskList):
    tasks: list[ReviewTask]
    deadline_day: int | None
    findings: list[ReviewFinding]
    deadline_candidates: list[DeadlineCandidate] = Field(default_factory=list)
