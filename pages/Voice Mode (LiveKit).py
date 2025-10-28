# pages/Voice Mode (LiveKit).py
# GrokMind Fusion — Voice Mode v2 (one-button popout, minimal UI, logging)

from __future__ import annotations
import json, os, time, uuid
import streamlit as st

import tools  # grok_chat, livekit_token, n8n_post

# Optional logger; safe fallbacks
try:
    from session_log import start_session, log_event, flush_events
except Exception:
    def start_session(**kw): return {"id": f"sess-{uuid.uuid4().hex[:8]}", "ts": int(time.time())}
    def log_event(_session, _event, **_data): pass
    def flush_events(_session): pass

st.set_page_config(page_title="Voice Mode (LiveKit)", layout="centered")

# One session per tab
if "gmf_session" not in st.session_state:
    st.session_state.gmf_session = start_session(app="gmf", page="voice_mode_v2")
SESSION = st.session_state.gmf_session

st.title("🎙️ Voice Mode")
st.caption(f"Session: `{SESSION['id']}` • One-button popout")

# Fixed room (simple), randomized identity for each launch
ROOM = "mindfusion"

def _rand_identity() -> str:
    return f"user-{uuid.uuid4().hex[:6]}"

with st.expander("Environment (debug)"):
    LIVEKIT_URL = st.secrets.get("LIVEKIT_URL", "wss://cloud.livekit.io")
    LIVEKIT_API_KEY = st.secrets.get("LIVEKIT_API_KEY")
    LIVEKIT_API_SECRET = st.secrets.get("LIVEKIT_API_SECRET")
    N8N_LOG_URL = st.secrets.get("N8N_LOG_URL", "")
    mask = lambda v: (v[:4] + "…" + v[-4:]) if v and len(v) > 8 else (v or "—")
    st.code(
        f"""LIVEKIT_URL: {LIVEKIT_URL}
LIVEKIT_API_KEY: {mask(LIVEKIT_API_KEY)}
LIVEKIT_API_SECRET: {mask(LIVEKIT_API_SECRET)}
N8N_LOG_URL: {"set" if N8N_LOG_URL else "(not set)"}""",
        language="bash",
    )

st.markdown("---")
st.subheader("Start")

if st.button("🚀 Start Voice Mode", type="primary", use_container_width=True):
    identity = _rand_identity()
    try:
        info = tools.livekit_token(ROOM, identity, name=identity)
        log_event(SESSION, "voice_mode_launch", room=ROOM, identity=identity)
    except Exception as e:
        log_event(SESSION, "livekit_token_err", error=str(e))
        st.error(f"LiveKit token failed: {e}")
        st.stop()

    # Minimal, high-contrast popout with UMD loader + explicit audio gesture
    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Voice Mode</title>
  <style>
    :root {{
      --bg:#0b0e12; --panel:#0f1520; --border:#1f2937; --text:#e8f0fe; --muted:#b7c4d9; --brand:#2563eb;
    }}
    html,body {{ background:var(--bg); color:var(--text); font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif; margin:0 }}
    .wrap {{ max-width:900px; margin:18px auto; padding:0 16px }}
    h2 {{ margin:8px 0 12px }}
    .row {{ display:flex; gap:10px; flex-wrap:wrap; margin:8px 0 14px }}
    button {{ padding:10px 14px; border:0; border-radius:10px; background:var(--brand); color:#fff; cursor:pointer }}
    button.secondary {{ background:#2a3550 }}
    .card {{ background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:14px }}
    .badges {{ display:flex; gap:8px; flex-wrap:wrap }}
    .badge {{ font-size:12px; background:#101826; border:1px solid var(--border); color:var(--muted); padding:6px 10px; border-radius:999px }}
    #status {{ white-space:pre-wrap; line-height:1.35; font-size:14px; color:var(--muted); margin-top:8px }}
  </style>
</head>
<body>
<div class="wrap">
  <h2>LiveKit: {ROOM}</h2>
  <div class="badges">
    <div class="badge" id="conn">Opening…</div>
    <div class="badge" id="mic">Mic OFF</div>
    <div class="badge">You: {identity}</div>
  </div>
  <div class="card">
    <div class="row">
      <button id="startAudio" class="secondary">🔈 Start Audio (unmute iOS)</button>
      <button id="toggleMic">🎙️ Toggle Mic</button>
      <button id="leave" class="secondary">🚪 Leave</button>
    </div>
    <div id="status">Loading client…</div>
  </div>
</div>

<script>
(function() {{
  const url = {json.dumps(info["url"])};
  const token = {json.dumps(info["token"])};

  function log(msg) {{
    const s = document.getElementById('status');
    console.log(msg);
    s.textContent += "\\n" + msg;
  }}

  // Popout window (we are already the popout), just boot LiveKit
  const UMD = "https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js";
  const s = document.createElement('script');
  s.src = UMD;
  s.onload = boot;
  s.onerror = () => document.getElementById('status').textContent = "Failed to load LiveKit UMD.";
  document.head.appendChild(s);

  function boot() {{
    if (!window.LiveKit || !window.LiveKit.Room) {{
      document.getElementById('status').textContent = "LiveKit UMD missing.";
      return;
    }}
    const Room = window.LiveKit.Room;
    const room = new Room({{ adaptiveStream:true, dynacast:true, publishDefaults:{{ dtx:true }} }});
    window.__lkRoom = room;

    room.on('trackSubscribed', (track, pub, participant) => {{
      if (track.kind === 'audio') {{
        const el = track.attach(); el.autoplay = true; el.playsInline = true; el.play().catch(()=>{{}});
        document.body.appendChild(el);
        log("Remote audio attached from " + (participant.identity || "peer"));
      }}
    }});
    room.on('participantConnected', p => log("participantConnected: " + p.identity));
    room.on('participantDisconnected', p => log("participantDisconnected: " + p.identity));
    room.on('disconnected', () => log("Disconnected."));

    document.getElementById('startAudio').onclick = () => {{
      try {{
        const A = new Audio();
        A.src = "data:audio/mp3;base64,//uQZAAAAAAAAAAAAAAAAAAAA";
        A.play().then(() => log("Audio primed")).catch(e => log("Audio prime failed: " + String(e)));
      }} catch (e) {{ log("Audio button error: " + String(e)); }}
    }};

    document.getElementById('toggleMic').onclick = async () => {{
      try {{
        const was = room.localParticipant.isMicrophoneEnabled; // property
        const now = await room.localParticipant.setMicrophoneEnabled(!was);
        document.getElementById('mic').textContent = now ? "Mic ON" : "Mic OFF";
        log(now ? "Mic ON" : "Mic OFF");
      }} catch (e) {{ log("Mic toggle failed: " + String(e)); }}
    }};

    document.getElementById('leave').onclick = () => {{
      try {{ room.disconnect(); log("Disconnected"); }} catch (e) {{ log("Leave failed: " + String(e)); }}
    }};

    room.connect(url, token).then(() => {{
      document.getElementById('conn').textContent = "Connected";
      log("Connected. Tap 🔈 Start Audio if iOS blocks sound.");
    }}).catch(e => {{
      document.getElementById('conn').textContent = "Connect failed";
      log("Connect failed: " + String(e));
    }});
  }}
}})();
</script>
</body>
</html>
"""
    # Open a real popout window from Streamlit
    st.components.v1.html(
        f"""
<script>
  const w = window.open("", "_blank", "popup,width=900,height=700");
  w.document.write({json.dumps(html)});
  w.document.close();
</script>
""",
        height=1,
    )

st.markdown("---")
st.caption("ONE button. Popout handles the rest. Logs go to n8n/Dropbox. ✅")
flush_events(SESSION)