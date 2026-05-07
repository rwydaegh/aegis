"""Wrapper around claude-agent-sdk for circa. Single long-lived session per server process.

Uses isinstance(msg, AssistantMessage) / isinstance(blk, TextBlock) — the SDK does NOT
expose a `.type` attribute on content blocks, so duck-typing on `.type` would silently
fail.
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any, Callable, Optional

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
)

from .annotation import Annotation
from .batch_protocol import build_batch_text, parse_status_block, ParseFallback


_DEFAULT_BATCH_TIMEOUT = 180


def _build_system_prompt(
    paper_dir: Path, paper_outline: str, pdfcomment_enabled: bool, tells_path: Optional[Path]
) -> str:
    style = paper_dir / ".circa" / "style.md"
    style_text = style.read_text() if style.exists() else ""
    tells_text = ""
    if tells_path and tells_path.exists():
        tells_text = tells_path.read_text()
    pdfc_rule = (
        "After every closing fence, on its own line, append "
        "`\\pdfcomment[author={circa}]{<short summary>} % [circa:<id>]`."
        if pdfcomment_enabled
        else "Do NOT use \\pdfcomment; only emit % [circa:<id>] tag comments."
    )
    return f"""You are circa's editor for paper.tex. You receive batched annotations from a reading pass.

For mode=edit annotations: apply the requested edit. Wrap every edit in
  % [circa:<id>:begin]
  ...changed lines...
  % [circa:<id>:end]
fence comments. {pdfc_rule}

For mode=ask annotations: do NOT edit; reply via the JSON `clarification` field only.

Conflict policy: two annotations are 'overlapping' if their fenced ranges in paper.tex would
intersect (NOT merely touch the same paragraph). For overlaps, EITHER merge into one fence
tagged % [circa:<id1>+<id2>:begin] / :end (both ids report `status: done` with
`one_liner = 'merged with <other id>: <summary>'`), OR set one to `needs_clarification` and
edit only the other.

Do not change numbers, equations, or citations without first asking via clarification.

End every response with a JSON block on its own line:
```circa-status
{{"<id>": {{"status": "done"|"needs_clarification", "one_liner": "...", "clarification": "..."}}, ...}}
```
Every annotation id in the batch MUST appear in the JSON block.

PAPER OUTLINE
{paper_outline}

WRITING TELLS TO AVOID
{tells_text}

PER-PAPER STYLE NOTES
{style_text}
"""


class ClaudeSession:
    def __init__(
        self,
        paper_dir: Path,
        system_prompt: str,
        batch_timeout_s: int = _DEFAULT_BATCH_TIMEOUT,
        _client_factory: Optional[Callable[[ClaudeAgentOptions], Any]] = None,
        _assistant_message_cls=AssistantMessage,
        _text_block_cls=TextBlock,
    ) -> None:
        self.paper_dir = paper_dir
        self.system_prompt = system_prompt
        self.batch_timeout_s = batch_timeout_s
        self._factory = _client_factory or (lambda opts: ClaudeSDKClient(options=opts))
        self._client = None
        self._AssistantMessage = _assistant_message_cls
        self._TextBlock = _text_block_cls

    @classmethod
    def with_default_prompt(
        cls,
        paper_dir: Path,
        paper_outline: str,
        pdfcomment_enabled: bool,
        tells_path: Optional[Path] = None,
        batch_timeout_s: int = _DEFAULT_BATCH_TIMEOUT,
    ) -> "ClaudeSession":
        prompt = _build_system_prompt(paper_dir, paper_outline, pdfcomment_enabled, tells_path)
        return cls(paper_dir=paper_dir, system_prompt=prompt, batch_timeout_s=batch_timeout_s)

    async def start(self) -> None:
        opts = ClaudeAgentOptions(system_prompt=self.system_prompt)
        self._client = self._factory(opts)
        await self._client.__aenter__()

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None

    async def send_batch(
        self,
        pass_: int,
        annotations: list[Annotation],
        page_pngs: dict[int, bytes],
        build_status_text: str,
    ) -> tuple[dict[str, dict[str, Any]], ParseFallback]:
        assert self._client is not None
        unique_pages = sorted({a.page for a in annotations})
        text_block = build_batch_text(pass_, annotations, build_status_text)
        content: list[dict[str, Any]] = []
        for pg in unique_pages:
            png = page_pngs.get(pg, b"")
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(png).decode("ascii"),
                    },
                }
            )
        content.append({"type": "text", "text": text_block})

        async def _gen():
            yield {
                "type": "user",
                "message": {"role": "user", "content": content},
                "parent_tool_use_id": None,
                "session_id": "default",
            }

        try:
            await asyncio.wait_for(self._client.query(_gen()), timeout=self.batch_timeout_s)
            full_text = ""
            async for msg in self._client.receive_response():
                if isinstance(msg, self._AssistantMessage):
                    for blk in msg.content:
                        if isinstance(blk, self._TextBlock):
                            full_text += blk.text
        except asyncio.TimeoutError:
            return (
                {
                    a.id: {
                        "status": "needs_clarification",
                        "clarification": "Claude timed out; try again or simplify the note.",
                    }
                    for a in annotations
                },
                ParseFallback.TIMEOUT,
            )

        return parse_status_block(full_text, expected_ids=[a.id for a in annotations])
