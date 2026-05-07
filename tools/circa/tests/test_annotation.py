import json
from server.annotation import Annotation, AnnotationMode, AnnotationStatus


def test_round_trip():
    a = Annotation(
        id="abc",
        page=7,
        shape="pen",
        points=[(0.1, 0.2), (0.3, 0.4)],
        text="rephrase",
        mode=AnnotationMode.EDIT,
        status=AnnotationStatus.PENDING,
        pass_=1,
        created_at=1700000000,
    )
    b = Annotation.from_dict(json.loads(json.dumps(a.to_dict())))
    assert b == a


def test_text_marker_single_anchor():
    a = Annotation(
        id="x",
        page=1,
        shape="text",
        points=[(0.5, 0.5)],
        text="?",
        mode=AnnotationMode.ASK,
        status=AnnotationStatus.PENDING,
        pass_=1,
        created_at=0,
    )
    assert len(a.points) == 1


def test_status_transitions():
    a = Annotation(
        id="x",
        page=1,
        shape="rect",
        points=[(0, 0), (1, 1)],
        text="x",
        mode=AnnotationMode.EDIT,
        status=AnnotationStatus.PENDING,
        pass_=1,
        created_at=0,
    )
    a.status = AnnotationStatus.IN_PROGRESS
    a.status = AnnotationStatus.DONE
    a.one_liner = "fixed"
    assert a.status == AnnotationStatus.DONE and a.one_liner == "fixed"
