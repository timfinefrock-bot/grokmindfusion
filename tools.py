# tools.py — minimal GrokMind Fusion "brain" wrapper
# Simple & Safe: loads keys from .env, talks to xAI (OpenAI-compatible)
# Includes helper to send JSON events to n8n cloud/webhook.

import os
import time
import requests
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

# Load .env for local dev; in Docker you'll pass envs with --env-file
load_dotenv()

# Defaults (override via .env)
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
XAI_MODEL = os.getenv("XAI_MODEL", "grok-4")

def _client() -> OpenAI:
    """Return an authenticated OpenAI (xAI) client."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise RuntimeError("XAI_API_KEY is not set. Add it to your .env.")
    return OpenAI(api_key=api_key, base_url=XAI_BASE_URL)

def grok_chat(prompt: str, *, model: Optional[str] = None,
              temperature: float = 0.2, system: Optional[str] = None) -> str:
    """
    Minimal chat completion call to xAI (Grok).
    Returns text content, or raises RuntimeError with readable message.
    """
    client = _client()
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})

    try:
        resp = client.chat.completions.create(
            model=model or XAI_MODEL,
            messages=msgs,
            temperature=temperature,
        )
        # defensive: handle empty responses
        if not resp.choices or not resp.choices[0].message or not resp.choices[0].message.content:
            raise RuntimeError("Empty response from Grok.")
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"Grok chat failed: {e}")

def n8n_post(event: str, data: dict | None = None) -> dict:
    """
    Send a JSON event to your n8n Production Webhook from Mind Fusion.
    """
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
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {"status": "ok", "raw": resp.text}