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

from . import paths
from .annotation import Annotation
from .batch_protocol import build_batch_text, parse_status_block, ParseFallback


_DEFAULT_BATCH_TIMEOUT = 180


def _build_system_prompt(
    paper_dir: Path,
    paper_outline: str,
    pdfcomment_enabled: bool,
    tells_path: Optional[Path],
    tex_name: str = "paper.tex",
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
    return f"""You are circa's editor for {tex_name}. You receive batched annotations from a reading pass. Read and edit the file {tex_name} (in your working directory) to apply them.

For mode=edit annotations: apply the requested edit. Wrap every edit in
  % [circa:<id>:begin]
  ...changed lines...
  % [circa:<id>:end]
fence comments. {pdfc_rule}

CRITICAL: each fence marker MUST be on its OWN LINE with NOTHING after the
closing `]`. Never put text on the same line as a `% [circa:...:begin]` or
`% [circa:...:end]` marker. Because the line starts with `%`, any trailing
text on the same line is silently commented out by LaTeX. If you insert a
fence in the middle of a line, split that line so the fence marker stands
alone and any continuation prose starts on a NEW line.

PAPERMAKER SOURCE SYNC
This paper may be assembled from a PaperMaker source tree in `main/` (sibling
leaf `.md` files, each holding one paragraph, figure, or table). In that case
{tex_name} is the ASSEMBLED output, so any edit you make to {tex_name} alone is
lost the next time the tree is re-assembled. To make edits durable, mirror every
mode=edit annotation back into the leaf it came from. After step 1 below has
edited {tex_name}, do steps 2 to 4 whenever a `main/` directory exists:

1. Apply the edit in {tex_name} with the fence markers, exactly as above.
2. Find the source leaf. Grep `main/` for a distinctive phrase from the region
   you edited, searching the real LaTeX (ignore `% PREV:` and `% NEXT:` lines:
   those are auto-generated previews of neighbouring leaves, not the leaf's own
   content). The leaf's build block is everything from the top of the file down
   to the first `## ` markdown heading.
3. Apply the SAME prose change to that leaf's build block. Do NOT copy the
   `% [circa:<id>...]` fence markers into the leaf; they belong only in the
   assembled {tex_name}.
4. Record the change for future agents. Below the LaTeX, under a `## Circa edits`
   heading (create it if absent; it sits after the build block, so it never
   reaches the assembled output), append one bullet:
   `- [circa:<id>] <what you changed and why>`.

If you cannot confidently locate the leaf, still apply the {tex_name} edit and
say so in that annotation's `one_liner` (for example, 'leaf not synced: <reason>')
so a human can port it by hand.

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
        self._session_id: Optional[str] = None

    @classmethod
    def with_default_prompt(
        cls,
        paper_dir: Path,
        paper_outline: str,
        pdfcomment_enabled: bool,
        tells_path: Optional[Path] = None,
        batch_timeout_s: int = _DEFAULT_BATCH_TIMEOUT,
        tex_name: str = "paper.tex",
    ) -> "ClaudeSession":
        prompt = _build_system_prompt(
            paper_dir, paper_outline, pdfcomment_enabled, tells_path, tex_name=tex_name
        )
        return cls(paper_dir=paper_dir, system_prompt=prompt, batch_timeout_s=batch_timeout_s)

    def _read_saved_session_id(self) -> Optional[str]:
        p = paths.session_id_file(self.paper_dir)
        if p.exists():
            return p.read_text().strip() or None
        return None

    def _persist_session_id(self, session_id: Optional[str]) -> None:
        """Remember the live session id so a later server restart can resume it."""
        if not session_id or session_id == "default" or session_id == self._session_id:
            return
        self._session_id = session_id
        try:
            paths.session_id_file(self.paper_dir).write_text(session_id)
        except OSError:
            pass

    def _build_options(self, resume: bool = True) -> ClaudeAgentOptions:
        kwargs: dict[str, Any] = {
            "system_prompt": self.system_prompt,
            "cwd": str(self.paper_dir),
        }
        if resume:
            saved = self._read_saved_session_id()
            if saved:
                kwargs["resume"] = saved
        return ClaudeAgentOptions(**kwargs)

    async def start(self) -> None:
        opts = self._build_options()
        self._client = self._factory(opts)
        try:
            await self._client.__aenter__()
        except Exception:
            # A saved session id can go stale (transcript pruned/moved). Fall back
            # to a fresh session rather than failing the whole server start.
            if getattr(opts, "resume", None) is None:
                raise
            opts = self._build_options(resume=False)
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
                self._persist_session_id(getattr(msg, "session_id", None))
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
