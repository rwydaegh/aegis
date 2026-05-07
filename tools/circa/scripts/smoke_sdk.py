"""Verify claude-agent-sdk 0.1.76 streaming-input + image content path.

Pass criteria:
  (a) at least one assistant text block received, parsed via isinstance(blk, TextBlock)
  (b) response stream completes cleanly
  (c) follow-up query() round-trips in the same context
"""

import asyncio
import base64
import io
import sys

from PIL import Image

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)


def _tiny_png_b64() -> str:
    img = Image.new("RGB", (32, 32), color=(180, 180, 180))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


async def main() -> int:
    png_b64 = _tiny_png_b64()
    SYS = "You are a terse assistant. Reply in one sentence."

    async def gen_with_image():
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": png_b64,
                        },
                    },
                    {"type": "text", "text": "What is the dominant color of the image? One word."},
                ],
            },
            "parent_tool_use_id": None,
            "session_id": "default",
        }

    opts = ClaudeAgentOptions(system_prompt=SYS)
    async with ClaudeSDKClient(options=opts) as client:
        await client.query(gen_with_image())
        first = ""
        async for msg in client.receive_response():
            print("MSG:", type(msg).__name__, repr(msg)[:200])
            if isinstance(msg, AssistantMessage):
                for blk in msg.content:
                    if isinstance(blk, TextBlock):
                        first += blk.text
        print("FIRST:", first[:200])
        assert first, "criterion (a) failed: no text in first response"

        async def gen2():
            yield {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Confirm you saw the previous image."},
                    ],
                },
                "parent_tool_use_id": None,
                "session_id": "default",
            }

        await client.query(gen2())
        second = ""
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for blk in msg.content:
                    if isinstance(blk, TextBlock):
                        second += blk.text
        print("SECOND:", second[:200])
        assert second, "criterion (c) failed: no text in second response"
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
