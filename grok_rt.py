# grok_rt.py
# GrokMind Fusion — ultra-light streaming facade for Grok.
# Cloud-safe: no audio drivers. Streams tokens to the caller.
from __future__ import annotations
import time
from typing import Iterable, Generator

try:
    import tools  # uses your existing grok_chat + secrets
except Exception as e:
    tools = None
    _TOOLS_ERR = str(e)

def stream_reply(prompt: str, *, chunk_ms: int = 40) -> Generator[str, None, None]:
    """
    Yields a reply as small chunks so the UI can render a 'streaming' effect.
    Uses tools.grok_chat under the hood for now (sync), then streams it out.
    This keeps us 100% Streamlit-Cloud compatible until Grok RT WS is enabled.
    """
    if not prompt.strip():
        return
    if not tools:
        # Fallback message if tools import failed
        text = f"(tools import failed: {_TOOLS_ERR}) You said: {prompt.strip()}"
    else:
        try:
            text = tools.grok_chat(prompt.strip())
        except Exception as e:
            text = f"(Grok error: {e}) You said: {prompt.strip()}"

    # Stream a few words at a time for nice effect
    words = text.split()
    buf = []
    for w in words:
        buf.append(w)
        # push 2–3 words at a time
        if len(buf) >= 3:
            yield " ".join(buf) + " "
            buf.clear()
            # gentle pacing so the UI can update; short to stay snappy
            time.sleep(chunk_ms / 1000.0)
    if buf:
        yield " ".join(buf)