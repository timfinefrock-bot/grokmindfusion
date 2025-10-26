# app.py — GrokMind Fusion (stable)
# Status + Chat + Transcribe + LiveKit + Builder (n8n)

from __future__ import annotations

import os
import uuid
import json
import tempfile
import requests
import streamlit as st

# Local modules
import tools
import voice

# ---------------------------
# Helpers
# ---------------------------
def _secret(key: str, default: str | None = None) -> str | None:
    """Safe secrets getter: prefers Streamlit secrets; falls back to env."""
    try:
        _ = st.secrets  # parse once
        return st.secrets.get(key, default)  # type: ignore[attr-defined]
    except Exception:
        return os.getenv(key, default)

def masked(val: str | None, keep: int = 4) -> str:
    if not val:
        return "—"
    return (val[:keep] + "…" + val[-keep:]) if len(val) > keep * 2 else "•••"

# ---------------------------
# Config / Secrets
# ---------------------------
N8N_BUILDER_URL = _secret("N8N_BUILDER_URL")
XAI_API_KEY = _secret("XAI_API_KEY")
ASSEMBLYAI_API_KEY = _secret("ASSEMBLYAI_API_KEY")
LIVEKIT_API_KEY = _secret("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = _secret("LIVEKIT_API_SECRET")
LIVEKIT_URL = _secret("LIVEKIT_URL") or "wss://cloud.livekit.io"
N8N_WORKSPACE_URL = _secret("N8N_WORKSPACE_URL")
STREAMLIT_ACCOUNT = _secret("STREAMLIT_ACCOUNT")

# ---------------------------
# n8n Builder client
# ---------------------------
def send_to_builder(repo_name: str, notes: str, priority: str, readme: str):
    """Send structured build request to n8n Builder webhook."""
    if not N8N_BUILDER_URL:
        return False, "Missing N8N_BUILDER_URL in Streamlit Cloud Secrets."

    payload = {
        "repo_name": repo_name.strip(),
        "private": True,
        "description": f"Created by GMF Builder v1 — priority={priority}" + (f" | {notes}" if notes else ""),
        "readme": readme or f"# {repo_name}\n\nBootstrapped by GMF Builder v1."
    }

    try:
        resp = requests.post(
            N8N_BUILDER_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        status = resp.status_code
        text = resp.text
    except requests.RequestException as e:
        return False, f"Request error: {e}"

    try:
        data = resp.json()
    except Exception:
        data = {"raw": text, "status": status}

    if 200 <= status < 300:
        return True, data
    else:
        return False, data

# ---------------------------
# UI setup
# ---------------------------
st.set_page_config(page_title="GrokMind Fusion", layout="centered")
st.title("🧠 GrokMind Fusion")

# ---- Environment ----
st.subheader("Environment")
def check_row(label, value):
    ok = bool(value)
    st.write(("✅" if ok else "🟡"), f"**{label}**", f"`{masked(value)}`" if value else " (not set)")
    return ok

_ = [
    check_row("XAI_API_KEY", XAI_API_KEY),
    check_row("ASSEMBLYAI_API_KEY", ASSEMBLYAI_API_KEY),
    check_row("LIVEKIT_API_KEY", LIVEKIT_API_KEY),
    check_row("LIVEKIT_API_SECRET", LIVEKIT_API_SECRET),
    check_row("LIVEKIT_URL", LIVEKIT_URL),
    check_row("N8N_WORKSPACE_URL", N8N_WORKSPACE_URL),
    check_row("STREAMLIT_ACCOUNT", STREAMLIT_ACCOUNT),
    check_row("N8N_BUILDER_URL", N8N_BUILDER_URL),
]
st.divider()

# ---- Chat with Grok ----
st.header("Chat with Grok")
user_text = st.text_area("Your message", placeholder="Type a question or instruction…", height=120)
log_n8n = st.checkbox("Post to n8n", value=True)

if st.button("Ask Grok", type="primary", use_container_width=True, disabled=not bool(user_text.strip())):
    try:
        reply = tools.grok_chat(user_text.strip())
        st.success("Grok replied:")
        st.write(reply)
        if log_n8n:
            try:
                tools.n8n_post("grok_reply", {"prompt": user_text.strip(), "reply": reply})
            except Exception as e:
                st.warning(f"n8n post failed: {e}")
    except Exception as e:
        st.error(f"Grok error: {e}")

st.divider()

# ---- Transcribe Audio ----
st.header("Transcribe Audio")
audio = st.file_uploader("Upload audio (aiff/wav/mp3/m4a)", type=["aiff", "wav", "mp3", "m4a"])
auto_ask = st.checkbox("Ask Grok about the transcript", value=True)
log_n8n2 = st.checkbox("Post to n8n", value=True, key="log2")

if st.button("Transcribe", use_container_width=True, disabled=audio is None):
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{audio.name}") as tmp:
            tmp.write(audio.getbuffer())
            tmp_path = tmp.name

        res = voice.transcribe_file(tmp_path)
        if "error" in res:
            st.error(f"AssemblyAI error: {res['error']}")
        else:
            txt = res.get("text", "").strip()
            st.success("Transcript:")
            st.write(txt)
            if log_n8n2:
                try:
                    tools.n8n_post("transcript_ready", {"text": txt, "confidence": res.get("confidence")})
                except Exception as e:
                    st.warning(f"n8n post failed: {e}")
            if auto_ask and txt:
                try:
                    reply = tools.grok_chat(f"You are Mind Fusion. Reply concisely to: {txt}")
                    st.info("Grok reply:")
                    st.write(reply)
                    if log_n8n2:
                        try:
                            tools.n8n_post(
                                "grok_reply_from_transcript",
                                {"input_text": txt, "reply": reply, "stt_conf": res.get("confidence")},
                            )
                        except Exception as e:
                            st.warning(f"n8n post failed: {e}")
                except Exception as e:
                    st.error(f"Grok error: {e}")
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

st.divider()

# ---- LiveKit Realtime ----
st.header("Realtime Voice (LiveKit)")
colA, colB = st.columns(2)
with colA:
    room = st.text_input("Room name", value="mindfusion")
with colB:
    identity = st.text_input("Your identity", value=f"user-{uuid.uuid4().hex[:6]}")
enabled = bool(LIVEKIT_API_KEY and LIVEKIT_API_SECRET and room.strip() and identity.strip())

if st.button("Join Live Voice (beta)", disabled=not enabled, use_container_width=True):
    try:
        info = tools.livekit_token(room.strip(), identity.strip(), name=identity.strip())

        # UMD build + robust global detection + visible logs
        html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>LiveKit Join</title>
  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
  <style>
    body {{ font-family: sans-serif; }}
    .btn {{ padding:8px 12px; margin:6px; }}
    #status {{ margin:8px 8px 12px; }}
    #log {{ white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; background:#111; color:#0f0; padding:10px; border-radius:8px; max-height:200px; overflow:auto; }}
  </style>
</head>
<body>
  <h3>LiveKit Room: {room}</h3>
  <div id="status">Loading client…</div>
  <button class="btn" id="muteBtn">Toggle Mute</button>
  <button class="btn" id="leaveBtn">Leave</button>
  <div id="log"></div>

  <script>
  const log = (...a) => {{
    const el = document.getElementById('log');
    el.textContent += a.map(x => (typeof x === 'string' ? x : JSON.stringify(x))).join(' ') + "\\n";
    el.scrollTop = el.scrollHeight;
    console.log(...a);
  }};

  (async () => {{
    // Pick whichever global exists
    const LK = window.livekit || window.Livekit || window.LiveKit;
    if (!LK) {{
      document.getElementById('status').innerText = 'LiveKit client failed to load.';
      log('ERROR: No LiveKit global found (livekit/Livekit/LiveKit)');
      return;
    }}
    document.getElementById('status').innerText = 'Client loaded. Connecting…';

    const url = "{info['url']}";
    const token = "{info['token']}";
    const room = new LK.Room({{
      adaptiveStream: true,
      dynacast: true,
      publishDefaults: {{ dtx: true }},
    }});
    window.__lkRoom = room; // debug handle

    // helpers
    const setStatus = (t) => document.getElementById('status').innerText = t;

    // events
    room.on('connectionStateChanged', s => log('state:', s));
    room.on('participantConnected', p => log('peer+', p.identity));
    room.on('participantDisconnected', p => log('peer-', p.identity));
    room.on('trackSubscribed', (track, pub, participant) => {{
      if (track.kind === 'audio') {{
        const el = track.attach();
        el.autoplay = true; el.playsInline = true;
        el.play().catch(()=>{{}});
        document.body.appendChild(el);
        log('audio subscribed from', participant.identity);
      }}
    }});
    room.on('trackPublicationMuted', pub => log('pub muted:', pub.trackSid));
    room.on('trackPublicationUnmuted', pub => log('pub unmuted:', pub.trackSid));

    // buttons
    document.getElementById('muteBtn').onclick = async () => {{
      try {{
        const was = room.localParticipant.isMicrophoneEnabled();
        const now = await room.localParticipant.setMicrophoneEnabled(!was);
        setStatus(now ? 'Mic ON' : 'Mic OFF');
        log('toggle mic ->', now);
      }} catch (e) {{
        setStatus('Mic toggle failed'); log('ERR toggle', e);
      }}
    }};
    document.getElementById('leaveBtn').onclick = () => {{
      try {{ room.disconnect(); setStatus('Disconnected'); log('left'); }}
      catch(e) {{ setStatus('Leave failed'); log('ERR leave', e); }}
    }};

    // preflight mic permission (don’t publish; just warm the permission)
    try {{
      await navigator.mediaDevices.getUserMedia({{ audio: true }});
      log('mic permission ok');
    }} catch (e) {{
      log('mic permission denied', e);
    }}

    try {{
      await room.connect(url, token);
      setStatus('Connected. Mic OFF by default—click Toggle Mute to speak.');
      log('connected');
    }} catch (e) {{
      setStatus('Connection failed: ' + e); log('ERR connect', e);
    }}
  }})();
  </script>
</body>
</html>
"""
        st.components.v1.html(html, height=520)
        st.success("LiveKit client loaded. Use the buttons to mute/unmute and leave.")
    except Exception as e:
        st.error(f"LiveKit token failed: {e}")

st.divider()

# ---- Builder (send spec to n8n) ----
st.header("Builder (send spec to n8n)")
col1, col2 = st.columns(2)
with col1:
    repo_name = st.text_input("Repository name", value="gmf-builder-demo").strip()
with col2:
    priority = st.selectbox("Priority", ["low", "normal", "high"], index=1)

notes = st.text_input("Notes (optional)", placeholder="Design preferences, tech stack, etc.")
readme = st.text_area("README content (optional)", height=120, placeholder="# Title\n\nShort description…")

if st.button("Send Build Request", use_container_width=True, disabled=not bool(repo_name)):
    ok, result = send_to_builder(repo_name, notes, priority, readme)
    if ok:
        repo_url = (result or {}).get("repo_url") or "(pending)"
        st.success(f"Builder started successfully. Repo: {repo_url}")
        with st.expander("Response (debug)"):
            st.code(json.dumps(result, indent=2))
    else:
        st.error("Builder request failed.")
        with st.expander("Error details"):
            st.code(json.dumps(result, indent=2) if isinstance(result, dict) else str(result))

st.caption("GrokMind Fusion — cloud app. Secrets are stored in Streamlit Cloud Secrets.")