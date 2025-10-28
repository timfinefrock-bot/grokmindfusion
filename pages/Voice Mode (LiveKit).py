# pages/Voice Mode (LiveKit).py
# GrokMind Fusion — Voice Mode (LiveKit) with dictation, streaming reply, and mobile-safe TTS
from __future__ import annotations

import json, os, time, uuid
import streamlit as st

import tools               # grok_chat, livekit_token, n8n_post
import grok_rt             # stream_reply(prompt)

# --- session logger (safe shims) ---
try:
    from session_log import start_session, log_event, flush_events
except Exception:
    def start_session(**kw): return {"id": f"sess-{uuid.uuid4().hex[:8]}", "ts": int(time.time())}
    def log_event(_s, _e, **_d): pass
    def flush_events(_s): pass

# ---------------------------
# Page / Session setup
# ---------------------------
st.set_page_config(page_title="Voice Mode (LiveKit)", layout="centered")

if "gmf_session" not in st.session_state:
    st.session_state.gmf_session = start_session(app="gmf", page="voice_mode")
SESSION = st.session_state.gmf_session
os.environ["GMF_SESSION_ID"] = SESSION.get("id", "")

st.title("🎙️ Voice Mode (LiveKit)")
st.caption(f"Session: `{SESSION['id']}`")

# ---------------------------
# Inputs
# ---------------------------
colA, colB = st.columns(2)
with colA:
    room = st.text_input("Room name", value="mindfusion").strip()
with colB:
    identity = st.text_input("Your identity", value="user").strip()

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

# ---------------------------
# Join LiveKit (inline widget)
# ---------------------------
st.subheader("Join room")
if st.button("🚀 Launch Voice (inline)", use_container_width=True):
    try:
        info = tools.livekit_token(room or "mindfusion", identity or "user", name=identity or "user")
        log_event(SESSION, "livekit_token_ok", room=room, identity=identity)
    except Exception as e:
        log_event(SESSION, "livekit_token_err", error=str(e))
        st.error(f"LiveKit token failed: {e}")
        st.stop()

    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Voice Mode</title>
  <style>
    :root {{
      --bg: #0b0e12; --panel:#0f1520; --panel2:#131a25; --border:#1f2937;
      --text:#e8f0fe; --muted:#a9b6cc; --brand:#1f6feb;
    }}
    html,body {{ background:var(--bg); color:var(--text); font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif; margin:0; }}
    .wrap {{ max-width:900px; margin:18px auto; padding:0 16px; }}
    .badges {{ display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 14px; }}
    .badge {{ font-size:12px; background:var(--panel2); border:1px solid var(--border); color:var(--muted); padding:6px 10px; border-radius:999px }}
    .card {{ background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:14px }}
    .row {{ display:flex; gap:10px; flex-wrap:wrap }}
    button {{ padding:10px 14px; border:0; border-radius:10px; background:var(--brand); color:#fff; cursor:pointer }}
    button.secondary {{ background:#2a3550 }}
    #status {{ white-space:pre-wrap; line-height:1.35; font-size:14px; margin-top:8px; color:var(--muted) }}
  </style>
</head>
<body>
<div class="wrap">
  <h2>LiveKit Room: {room}</h2>
  <div class="badges">
    <div class="badge" id="conn">Connecting…</div>
    <div class="badge" id="mic">Mic OFF</div>
    <div class="badge">Waiting for peers…</div>
  </div>
  <div class="card">
    <div class="row">
      <button id="startAudioBtn" class="secondary">🔈 Start Audio (if muted by browser)</button>
      <button id="muteBtn">🎙️ Toggle Mic</button>
      <button id="leaveBtn" class="secondary">🚪 Leave</button>
    </div>
    <div id="status">Loading LiveKit client…</div>
  </div>
</div>

<script>
(async () => {{
  const status = document.getElementById('status');
  const badgeConn = document.getElementById('conn');
  const badgeMic  = document.getElementById('mic');
  const log = (...a) => {{ console.log(...a); status.textContent += "\\n" + a.join(" "); }};
  const UMD = [
    "https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js",
    "https://unpkg.com/livekit-client@2/dist/livekit-client.umd.min.js"
  ];
  const ESM = [
    "https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.esm.js",
    "https://unpkg.com/livekit-client@2/dist/livekit-client.esm.js",
    "https://esm.sh/livekit-client@2"
  ];
  function loadScript(src) {{
    return new Promise((resolve, reject) => {{
      const s = document.createElement('script'); s.src = src;
      s.onload = () => resolve(src); s.onerror = () => reject(new Error('script failed: ' + src));
      document.head.appendChild(s);
    }});
  }}
  async function tryUMD() {{ for (const u of UMD) {{ try {{ await loadScript(u); if (window.LiveKit?.Room) return window.LiveKit; }} catch (e) {{ log("UMD err", String(e)); }} }} return null; }}
  async function tryESM() {{ for (const u of ESM) {{ try {{ const m = await import(/* @vite-ignore */ u); return m; }} catch (e) {{ log("ESM err", String(e)); }} }} return null; }}
  let LK = await tryUMD(); if (!LK) LK = await tryESM(); if (!LK) {{ status.textContent = "LiveKit failed to load"; return; }}
  const Room = LK.Room; const room = new Room({{ adaptiveStream:true, dynacast:true, publishDefaults: {{ dtx:true }} }}); window.__lkRoom = room;

  room.on('trackSubscribed', (track, pub, p) => {{ if (track.kind==='audio') {{ const el=track.attach(); el.autoplay=true; el.playsInline=true; el.play().catch(()=>{{}}); document.body.appendChild(el); log("Remote audio attached"); }} }});
  document.getElementById('startAudioBtn').onclick = () => {{ try {{ const A=new Audio(); A.src="data:audio/mp3;base64,//uQZAAAA"; A.play().catch(()=>{{}}); log("Audio unlock gesture sent"); }} catch(e){{ log("unlock fail", String(e)); }} }};
  document.getElementById('muteBtn').onclick = async () => {{
    try {{
      const was = room.localParticipant.isMicrophoneEnabled;
      const now = await room.localParticipant.setMicrophoneEnabled(!was);
      badgeMic.textContent = now ? "Mic ON" : "Mic OFF";
      log(now ? "Mic ON" : "Mic OFF");
    }} catch (e) {{ log("Mic toggle failed:", String(e)); }}
  }};
  document.getElementById('leaveBtn').onclick = () => {{ try {{ room.disconnect(); log("Disconnected"); }} catch (e) {{ log("Leave failed", String(e)); }} }};
  const url = {json.dumps(info["url"])}; const token = {json.dumps(info["token"])};
  try {{ await room.connect(url, token); badgeConn.textContent = "Connected"; log("Connected. Mic OFF by default."); }} catch(e) {{ badgeConn.textContent="Connection failed"; log("Connect fail", String(e)); }}
}})();
</script>
</body>
</html>
"""
    st.components.v1.html(html, height=640, scrolling=True)
    log_event(SESSION, "livekit_widget_rendered", room=room, identity=identity)

st.markdown("---")

# ---------------------------
# Dictate + stream reply + TTS
# ---------------------------
st.subheader("🧠 Talk to Grok (quick demo)")

# Dictate button injects text into the textarea
st.markdown("""
<div id="gmf-dictate"></div>
<script>
(function(){
  const mount = document.getElementById('gmf-dictate');
  const btn = document.createElement('button');
  btn.textContent = "🎤 Dictate";
  btn.style = "padding:8px 12px;border:0;border-radius:8px;background:#2563eb;color:#fff;margin:6px 0;";
  btn.onclick = () => {
    if (!('webkitSpeechRecognition' in window)) { alert('Speech recognition not supported in this browser.'); return; }
    const r = new webkitSpeechRecognition();
    r.lang = 'en-US'; r.interimResults = false; r.continuous = false;
    r.onresult = (e) => {
      const text = e.results[0][0].transcript;
      const ta = parent.document.querySelector('textarea');
      if (ta) { ta.value = text; ta.dispatchEvent(new Event('input', {bubbles:true})); }
    };
    r.onerror = () => r.stop(); r.start();
  };
  mount.appendChild(btn);
})();
</script>
""", unsafe_allow_html=True)

user_msg = st.text_area(
    "Say (or paste) something for Grok",
    height=70,
    placeholder="e.g., Summarize what GMF Builder does in 3 bullets."
)

colL, colR = st.columns([1, 1])
speak_btn     = colL.button("Send to Grok → Speak reply", type="primary", use_container_width=True)
just_text_btn = colR.button("Send to Grok (text only)",        use_container_width=True)

def speak_in_browser(text: str):
    st.components.v1.html(f"""
<div id="gmf-speak" style="margin-top:8px;">
  <button id="sbtn" style="padding:8px 12px;border:0;border-radius:8px;background:#16a34a;color:#fff;">🔊 Speaking…</button>
</div>
<script>
(function() {{
  const btn = document.getElementById('sbtn');
  const text = {json.dumps(text)};
  btn.onclick = () => {{
    try {{
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1.03; u.pitch = 1.0; u.lang = 'en-US';
      speechSynthesis.cancel(); speechSynthesis.speak(u);
    }} catch (e) {{ console.log("TTS failed:", e); }}
  }};
}})();
</script>
""", height=46)

def send_to_grok_and_show(prompt: str, speak: bool):
    msg = (prompt or "").strip()
    if not msg:
        st.warning("Type something first.")
        return
    try:
        log_event(SESSION, "grok_ask", text=msg)
        reply = tools.grok_chat(msg)
        st.success("Grok reply")
        st.write(reply)
        log_event(SESSION, "grok_reply", text=reply)
        try:
            tools.n8n_post("voice_demo_grok", {"session": SESSION["id"], "prompt": msg, "reply": reply})
        except Exception:
            pass
        if speak:
            speak_in_browser(reply)
    except Exception as e:
        st.error(f"Grok error: {e}")
        log_event(SESSION, "grok_err", error=str(e))

if speak_btn:     send_to_grok_and_show(user_msg, speak=True)
if just_text_btn: send_to_grok_and_show(user_msg, speak=False)

st.caption("Tip: On iPhone, tap the green button to play Grok’s reply (browser audio unlock).")

st.markdown("---")

# ---------------------------
# Full Duplex (beta): stream tokens to the page + TTS on tap
# ---------------------------
st.subheader("🔁 Full Duplex (beta, text-stream)")

if st.button("Start Grok RT stream (server-side)"):
    placeholder = st.empty()
    streamed = []
    for chunk in grok_rt.stream_reply(user_msg or "Say hello."):
        streamed.append(chunk)
        placeholder.markdown("**Streaming…**  \n" + "".join(streamed))
    final = "".join(streamed).strip()
    if final:
        st.success("Assistant (final):")
        st.write(final)
        speak_in_browser(final)
        log_event(SESSION, "grok_stream_final", text=final)
        try:
            tools.n8n_post("voice_stream_final", {"session": SESSION["id"], "prompt": user_msg, "reply": final})
        except Exception:
            pass

flush_events(SESSION)