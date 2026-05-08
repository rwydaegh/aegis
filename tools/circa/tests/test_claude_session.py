"""Wrapper logic only. Real SDK exercised via Task 9 smoke."""

import asyncio  # noqa: F401  # used implicitly by wait_for path; keep per task spec
from dataclasses import dataclass

import pytest

from server.annotation import Annotation, AnnotationMode, AnnotationStatus
from server.claude_session import ClaudeSession


# Minimal stand-ins matching the real SDK's class shape.
@dataclass
class FakeTextBlock:
    text: str


@dataclass
class FakeAssistantMessage:
    content: list


class FakeClient:
    def __init__(self, scripted: str = ""):
        self.queries: list[dict] = []
        self.scripted = scripted

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def query(self, gen):
        async for env in gen:
            self.queries.append(env)

    async def receive_response(self):
        yield FakeAssistantMessage(content=[FakeTextBlock(text=self.scripted)])


def _ann(id="a1", page=1, text="x"):
    return Annotation(
        id=id,
        page=page,
        shape="rect",
        points=[(0, 0), (1, 1)],
        text=text,
        mode=AnnotationMode.EDIT,
        status=AnnotationStatus.PENDING,
        pass_=1,
        created_at=0,
    )


@pytest.mark.asyncio
async def test_send_batch_emits_query_with_text_and_image(paper_dir):
    fake = FakeClient(scripted='```circa-status\n{"a1": {"status": "done", "one_liner": "ok"}}\n```')
    sess = ClaudeSession(
        paper_dir=paper_dir,
        system_prompt="SYS",
        _client_factory=lambda opts: fake,
        _assistant_message_cls=type(FakeAssistantMessage(content=[])),
        _text_block_cls=type(FakeTextBlock(text="")),
    )
    await sess.start()
    statuses, _ = await sess.send_batch(
        pass_=1,
        annotations=[_ann()],
        page_pngs={1: b"PNGBYTES"},
        build_status_text="ok",
    )
    assert statuses["a1"]["status"] == "done"
    env = fake.queries[0]
    types = [b["type"] for b in env["message"]["content"]]
    assert "image" in types and "text" in types


@pytest.mark.asyncio
async def test_send_batch_dedupes_pages(paper_dir):
    fake = FakeClient(scripted='```circa-status\n{"a1": {"status": "done"}, "a2": {"status": "done"}}\n```')
    sess = ClaudeSession(
        paper_dir=paper_dir,
        system_prompt="SYS",
        _client_factory=lambda opts: fake,
        _assistant_message_cls=type(FakeAssistantMessage(content=[])),
        _text_block_cls=type(FakeTextBlock(text="")),
    )
    await sess.start()
    await sess.send_batch(
        pass_=1,
        annotations=[_ann("a1"), _ann("a2")],  # both page 1
        page_pngs={1: b"PNG"},
        build_status_text="ok",
    )
    images = [b for b in fake.queries[0]["message"]["content"] if b["type"] == "image"]
    assert len(images) == 1


@pytest.mark.asyncio
async def test_send_batch_handles_missing_status_block(paper_dir):
    fake = FakeClient(scripted="no fence")
    sess = ClaudeSession(
        paper_dir=paper_dir,
        system_prompt="SYS",
        _client_factory=lambda opts: fake,
        _assistant_message_cls=type(FakeAssistantMessage(content=[])),
        _text_block_cls=type(FakeTextBlock(text="")),
    )
    await sess.start()
    statuses, _ = await sess.send_batch(
        pass_=1,
        annotations=[_ann()],
        page_pngs={1: b"PNG"},
        build_status_text="ok",
    )
    assert statuses["a1"]["status"] == "needs_clarification"
