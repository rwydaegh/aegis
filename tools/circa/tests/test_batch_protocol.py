from server.annotation import Annotation, AnnotationMode, AnnotationStatus
from server.batch_protocol import build_batch_text, parse_status_block, ParseFallback


def _ann(id="a", text="", mode=AnnotationMode.EDIT):
    return Annotation(
        id=id,
        page=1,
        shape="rect",
        points=[(0.1, 0.1), (0.5, 0.5)],
        text=text,
        mode=mode,
        status=AnnotationStatus.PENDING,
        pass_=1,
        created_at=0,
    )


def test_build_includes_ids_and_protocol():
    text = build_batch_text(
        pass_=1,
        annotations=[_ann("a1", "rephrase"), _ann("a2", "?", AnnotationMode.ASK)],
        build_status_text="ok",
    )
    assert "a1" in text and "a2" in text and "rephrase" in text and "circa-status" in text


def test_build_includes_broken_prepend():
    text = build_batch_text(pass_=1, annotations=[_ann("a1")], build_status_text="broken: ! Undefined macro")
    assert "build is broken" in text.lower()


def test_parse_happy():
    msg = '```circa-status\n{"a1": {"status": "done", "one_liner": "rephrased"}}\n```'
    statuses, fb = parse_status_block(msg, ["a1"])
    assert fb == ParseFallback.OK and statuses["a1"]["status"] == "done"


def test_parse_missing():
    statuses, fb = parse_status_block("no fence", ["a1"])
    assert fb == ParseFallback.MISSING and statuses["a1"]["status"] == "needs_clarification"


def test_parse_malformed():
    statuses, fb = parse_status_block("```circa-status\n{not json\n```", ["a1"])
    assert fb == ParseFallback.MALFORMED and statuses["a1"]["status"] == "needs_clarification"


def test_parse_partial():
    msg = '```circa-status\n{"a1": {"status": "done", "one_liner": "x"}}\n```'
    statuses, fb = parse_status_block(msg, ["a1", "a2"])
    assert fb == ParseFallback.PARTIAL and statuses["a2"]["status"] == "needs_clarification"


def test_parse_unknown_ignored():
    msg = '```circa-status\n{"a1": {"status": "done"}, "ZZZ": {"status": "done"}}\n```'
    statuses, _ = parse_status_block(msg, ["a1"])
    assert "ZZZ" not in statuses


def test_parse_multiple_takes_last():
    msg = """```circa-status
{"a1": {"status": "done", "one_liner": "first"}}
```
text
```circa-status
{"a1": {"status": "done", "one_liner": "last"}}
```"""
    statuses, _ = parse_status_block(msg, ["a1"])
    assert statuses["a1"]["one_liner"] == "last"
