import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .annotation import Annotation


@dataclass
class State:
    server_instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_pass: int = 1
    in_flight: bool = False
    last_build_ok: bool = True
    last_build_error: str = ""
    _seq: int = 0
    _annotations: dict[str, Annotation] = field(default_factory=dict)
    _next_clar: list[dict[str, Any]] = field(default_factory=list)
    _next_new: list[dict[str, Any]] = field(default_factory=list)

    def next_seq(self) -> int:
        self._seq += 1
        return self._seq

    @property
    def last_seq(self) -> int:
        return self._seq

    def add_annotation(self, a: Annotation) -> None:
        self._annotations[a.id] = a

    def get_annotation(self, id: str) -> Optional[Annotation]:
        return self._annotations.get(id)

    def all_annotations(self) -> list[Annotation]:
        return list(self._annotations.values())

    def next_pass(self) -> int:
        self.current_pass += 1
        return self.current_pass

    def drop_annotations_below_pass(self, pass_: int) -> None:
        self._annotations = {id: a for id, a in self._annotations.items() if a.pass_ >= pass_}

    def queue_next_batch_clarification(self, payload: dict[str, Any]) -> None:
        self._next_clar.append(payload)

    def queue_next_batch_new(self, payload: dict[str, Any]) -> None:
        self._next_new.append(payload)

    def drain_next_batch(self) -> list[dict[str, Any]]:
        out = list(self._next_clar) + list(self._next_new)
        self._next_clar.clear()
        self._next_new.clear()
        return out
