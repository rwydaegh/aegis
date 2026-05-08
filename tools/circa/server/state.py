import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .annotation import Annotation


@dataclass
class State:
    server_instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_pass: int = 1
    in_flight: bool = False
    last_build_ok: bool = True
    last_build_error: str = ""
    save_path: Optional[Path] = None
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
        self.save()

    def get_annotation(self, id: str) -> Optional[Annotation]:
        return self._annotations.get(id)

    def all_annotations(self) -> list[Annotation]:
        return list(self._annotations.values())

    def next_pass(self) -> int:
        self.current_pass += 1
        self.save()
        return self.current_pass

    def drop_annotations_below_pass(self, pass_: int) -> None:
        self._annotations = {id: a for id, a in self._annotations.items() if a.pass_ >= pass_}
        self.save()

    def clear_done_below_pass(self, pass_: int) -> list[str]:
        removed = [
            id
            for id, a in self._annotations.items()
            if a.pass_ < pass_ and a.status.value in ("done", "needs_clarification", "rejected")
        ]
        for id in removed:
            del self._annotations[id]
        self.save()
        return removed

    def queue_next_batch_clarification(self, payload: dict[str, Any]) -> None:
        self._next_clar.append(payload)

    def queue_next_batch_new(self, payload: dict[str, Any]) -> None:
        self._next_new.append(payload)

    def drain_next_batch(self) -> list[dict[str, Any]]:
        out = list(self._next_clar) + list(self._next_new)
        self._next_clar.clear()
        self._next_new.clear()
        return out

    def save(self) -> None:
        if self.save_path is None:
            return
        payload = {
            "current_pass": self.current_pass,
            "annotations": [a.to_dict() for a in self._annotations.values()],
        }
        tmp = self.save_path.with_suffix(self.save_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(self.save_path)

    def load(self) -> None:
        if self.save_path is None or not self.save_path.exists():
            return
        try:
            payload = json.loads(self.save_path.read_text())
        except Exception:
            return
        self.current_pass = payload.get("current_pass", 1)
        for d in payload.get("annotations", []):
            try:
                a = Annotation.from_dict(d)
            except Exception:
                continue
            self._annotations[a.id] = a
