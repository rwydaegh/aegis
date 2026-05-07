from server.annotation import Annotation, AnnotationMode, AnnotationStatus
from server.state import State


def _ann(id="a", pass_=1):
    return Annotation(
        id=id,
        page=1,
        shape="rect",
        points=[(0, 0), (1, 1)],
        text="t",
        mode=AnnotationMode.EDIT,
        status=AnnotationStatus.PENDING,
        pass_=pass_,
        created_at=0,
    )


def test_seq_monotonic():
    s = State()
    assert (s.next_seq(), s.next_seq(), s.next_seq()) == (1, 2, 3)
    assert s.last_seq == 3


def test_server_instance_id_is_uuid():
    s = State()
    assert len(s.server_instance_id) == 36


def test_in_flight_default_false():
    assert not State().in_flight


def test_add_get_annotations():
    s = State()
    s.add_annotation(_ann("a"))
    assert s.get_annotation("a") is not None
    assert s.get_annotation("missing") is None


def test_pass_starts_at_one_and_increments():
    s = State()
    assert s.current_pass == 1
    assert s.next_pass() == 2 and s.current_pass == 2


def test_drop_below_pass():
    s = State()
    s.add_annotation(_ann("a", 1))
    s.add_annotation(_ann("b", 2))
    s.drop_annotations_below_pass(2)
    assert s.get_annotation("a") is None and s.get_annotation("b") is not None


def test_next_batch_priority_order():
    """Clarifications come out before new annotations (clarifications-first FIFO)."""
    s = State()
    s.queue_next_batch_new({"batch_id": "n1"})
    s.queue_next_batch_clarification({"batch_id": "c1"})
    s.queue_next_batch_new({"batch_id": "n2"})
    s.queue_next_batch_clarification({"batch_id": "c2"})
    drained = s.drain_next_batch()
    assert [d["batch_id"] for d in drained] == ["c1", "c2", "n1", "n2"]
