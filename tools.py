# 1) tools.py (final base)
# tools.py — GrokMind Fusion helpers (final base)
# xAI (Grok), n8n event post, LiveKit token signing (server-side safe), Builder helper

import os
import time
import requests
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
import jwt  # PyJWT

load_dotenv()

# ---- xAI (Grok) ----
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
XAI_MODEL = os.getenv("XAI_MODEL", "grok-4")

def _client() -> OpenAI:
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise RuntimeError("XAI_API_KEY is not set. Add it to your .env / secrets.")
    return OpenAI(api_key=api_key, base_url=XAI_BASE_URL)

def grok_chat(prompt: str, *, model: Optional[str] = None,
              temperature: float = 0.2, system: Optional[str] = None) -> str:
    client = _client()
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    try:
        resp = client.chat.completions.create(
            model=model or XAI_MODEL, messages=msgs, temperature=temperature,
        )
        if not resp.choices or not resp.choices[0].message or not resp.choices[0].message.content:
            raise RuntimeError("Empty response from Grok.")
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"Grok chat failed: {e}")

# ---- n8n event post ----
def n8n_post(event: str, data: dict | None = None) -> dict:
    url = os.getenv("N8N_WORKSPACE_URL")
    if not url:
        raise RuntimeError("N8N_WORKSPACE_URL is not set in your environment.")
    payload = {
        "event": event,
        "from": "mind-fusion",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if data is not None:
        payload["data"] = data
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {"status": "ok", "raw": resp.text}

# ---- Builder helper (sends structured build request to n8n) ----
def builder_task(spec: str, *, priority: str = "normal", notes: str = "") -> dict:
    if not spec.strip():
        raise RuntimeError("Builder spec is empty.")
    data = {"spec": spec.strip(), "priority": priority, "notes": notes}
    return n8n_post("build_request", data)

# -# ---- LiveKit token signing (server-side) ----
def livekit_token(room: str, identity: str, name: str | None = None, *, ttl_seconds: int = 3600) -> dict:
    """
    Create a LiveKit access token (JWT) for joining a room (LiveKit v2 format).
    - iss: LIVEKIT_API_KEY
    - sub: participant identity
    - signed HS256 with LIVEKIT_API_SECRET
    - top-level `video` grant (no "grants" wrapper)
    """
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    lk_url = os.getenv("LIVEKIT_URL") or "wss://cloud.livekit.io"
    if not api_key or not api_secret:
        raise RuntimeError("LIVEKIT_API_KEY/LIVEKIT_API_SECRET not set.")

    now = int(time.time())
    exp = now + ttl_seconds

    payload = {
        "iss": api_key,                 # MUST be your API key
        "sub": identity,                # participant identity
        "nbf": now - 10,                # small skew allowance
        "iat": now,
        "exp": exp,
        "name": (name or identity),
        "video": {                      # v2-style grant at top level
            "roomJoin": True,
            "room": room,
            "canPublish": True,
            "canSubscribe": True,
        },
    }

    # HS256 with your API SECRET. (No kid header required for v2)
    token = jwt.encode(payload, api_secret, algorithm="HS256")
    return {"url": lk_url, "token": token}