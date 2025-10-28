# grok_rt.py — Full duplex Grok RT voice loop (server-side beta, v0.3.5)
from __future__ import annotations
import os, json, asyncio, websockets, threading, queue, base64, time
import sounddevice as sd

GROK_RT_URL = os.getenv("GROK_RT_URL", "wss://api.x.ai/v1/realtime?model=grok-4-realtime-preview")
XAI_API_KEY = os.getenv("XAI_API_KEY")

if not XAI_API_KEY:
    raise RuntimeError("Missing XAI_API_KEY (env or Streamlit Secret via os.environ).")

AUDIO_RATE = 16000
AUDIO_BLOCK = 1024
_audio_q: "queue.Queue[bytes|None]" = queue.Queue()

def _audio_callback(indata, frames, time_info, status):
    if status:
        print("[sounddevice]", status)
    _audio_q.put(bytes(indata))

def start_input_stream():
    return sd.InputStream(
        channels=1,
        samplerate=AUDIO_RATE,
        blocksize=AUDIO_BLOCK,
        dtype="int16",
        callback=_audio_callback,
    )

async def _send_audio(ws):
    """Pull audio blocks from queue and send to Grok RT."""
    while True:
        chunk = _audio_q.get()
        if chunk is None:
            break
        b64 = base64.b64encode(chunk).decode()
        await ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": b64
        }))

async def voice_loop(prompt: str = "Hello, Grok!", max_seconds: int = 15):
    """
    Opens a websocket to Grok RT, streams mic audio, and prints RT messages.
    Note: this is server-side (uses sounddevice); not for Streamlit Cloud runtime.
    """
    headers = {"Authorization": f"Bearer {XAI_API_KEY}"}
    t0 = time.time()
    async with websockets.connect(GROK_RT_URL, extra_headers=headers, ping_interval=20) as ws:
        print("[GROK-RT] Connected.")

        # optional initial text
        await ws.send(json.dumps({"type": "input_text", "text": prompt}))

        # start mic thread
        def mic_thread():
            with start_input_stream():
                while time.time() - t0 < max_seconds:
                    # Audio chunks pushed by callback; just sleep a bit here
                    time.sleep(0.05)
                _audio_q.put(None)  # sentinel

        threading.Thread(target=mic_thread, daemon=True).start()

        # pump audio concurrently
        send_audio = asyncio.create_task(_send_audio(ws))

        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    print("[GROK-RT] (non-json)", raw[:120])
                    continue

                # Typical events (spec subject to change by API)
                if "output_audio" in msg:
                    print("[GROK-RT audio]", len(msg["output_audio"]))
                if "text" in msg:
                    print("[GROK-RT]", msg["text"])

                # exit after time
                if time.time() - t0 >= max_seconds:
                    break
        finally:
            send_audio.cancel()
            try:
                await ws.close()
            except Exception:
                pass
            print("[GROK-RT] Closed.")