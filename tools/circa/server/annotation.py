from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class AnnotationMode(str, Enum):
    EDIT = "edit"
    ASK = "ask"


class AnnotationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    NEEDS_CLARIFICATION = "needs_clarification"
    REJECTED = "rejected"


@dataclass
class Annotation:
    id: str
    page: int
    shape: str
    points: list[tuple[float, float]]
    text: str
    mode: AnnotationMode
    status: AnnotationStatus
    pass_: int
    created_at: int
    one_liner: str | None = None
    clarification: str | None = None
    reply: str | None = None
    parent_id: str | None = None
    batch_id: str | None = None
    linked_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        d["status"] = self.status.value
        d["pass"] = d.pop("pass_")
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Annotation":
        d = dict(d)
        d["mode"] = AnnotationMode(d["mode"])
        d["status"] = AnnotationStatus(d["status"])
        d["pass_"] = d.pop("pass")
        d["points"] = [tuple(p) for p in d["points"]]
        return cls(**d)
