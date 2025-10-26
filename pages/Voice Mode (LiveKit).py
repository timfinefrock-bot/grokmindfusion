# pages/Voice Mode (LiveKit).py
from __future__ import annotations
import json
import streamlit as st
import tools

st.set_page_config(page_title="Voice Mode (LiveKit)", layout="centered")
st.title("🎙️ Voice Mode (LiveKit)")

# ---------- Inputs ----------
room = st.text_input("Room name", value="mindfusion")
identity = st.text_input("Your identity", value="user")

with st.expander("Environment (debug)"):
    LIVEKIT_URL = st.secrets.get("LIVEKIT_URL", "wss://cloud.livekit.io")
    LIVEKIT_API_KEY = st.secrets.get("LIVEKIT_API_KEY")
    LIVEKIT_API_SECRET = st.secrets.get("LIVEKIT_API_SECRET")
    mask = lambda v: (v[:4] + "…" + v[-4:]) if v and len(v) > 8 else (v or "—")
    st.code(
        f"""LIVEKIT_URL: {LIVEKIT_URL}
LIVEKIT_API_KEY: {mask(LIVEKIT_API_KEY)}
LIVEKIT_API_SECRET: {mask(LIVEKIT_API_SECRET)}""",
        language="bash",
    )

# ---------- LiveKit inline launcher ----------
if st.button("🚀 Launch Voice (inline)", use_container_width=True):
    try:
        info = tools.livekit_token(
            room.strip() or "mindfusion",
            identity.strip() or "user",
            name=identity.strip() or "user"
        )
    except Exception as e:
        st.error(f"Token error: {e}")
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
      --bg: #0b0e12;
      --panel: #10151c;
      --panel-border: #1e2633;
      --text: #e8f0fe;
      --muted: #9db2d0;
      --brand: #1f6feb;
      --good: #12b886;
      --warn: #f08c00;
    }}
    html, body {{ background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif; margin:0; }}
    .wrap {{ max-width: 900px; margin: 18px auto; padding: 0 16px; }}
    h2 {{ margin: 8px 0 12px; }}
    .badges {{ display:flex; gap:8px; flex-wrap:wrap; margin: 8px 0 14px; }}
    .badge {{ font-size: 12px; background:#0e1420; border:1px solid var(--panel-border); color:var(--muted); padding:6px 10px; border-radius: 999px; }}
    .card {{ background: var(--panel); border:1px solid var(--panel-border); border-radius: 12px; padding: 14px; }}
    .row {{ display:flex; gap:10px; flex-wrap:wrap; }}
    button {{ padding:10px 14px; border:0; border-radius: 10px; background: var(--brand); color:#fff; cursor:pointer; }}
    button.secondary {{ background:#2a3550; }}
    #status {{ white-space: pre-wrap; line-height:1.35; font-size:14px; margin-top:8px; color: var(--muted); }}
  </style>
</head>
<body>
<div class="wrap">
  <h2>LiveKit Room: {room}</h2>
  <div class="badges">
    <div class="badge" id="conn">Waiting to connect…</div>
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

  // Loader tries UMD then ESM (3 CDNs total)
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
      const s = document.createElement('script');
      s.src = src;
      s.onload = () => resolve(src);
      s.onerror = () => reject(new Error('script failed: ' + src));
      document.head.appendChild(s);
    }});
  }}

  async function tryUMD() {{
    for (const url of UMD) {{
      try {{
        await loadScript(url);
        if (window.LiveKit?.Room) {{ log("UMD loaded:", url); return window.LiveKit; }}
      }} catch (e) {{ log("UMD error:", String(e)); }}
    }}
    return null;
  }}
  async function tryESM() {{
    for (const url of ESM) {{
      try {{
        const mod = await import(/* @vite-ignore */ url);
        log("ESM loaded:", url);
        return mod;
      }} catch (e) {{ log("ESM error:", String(e)); }}
    }}
    return null;
  }}

  let LK = await tryUMD();
  if (!LK) LK = await tryESM();
  if (!LK) {{ status.textContent = "ERROR: LiveKit failed to load from jsDelivr and unpkg (UMD & ESM)."; return; }}

  const Room = LK.Room;
  const room = new Room({{ adaptiveStream: true, dynacast: true, publishDefaults: {{ dtx: true }} }});
  window.__lkRoom = room;

  // Events
  room.on('participantConnected', p => log("participantConnected:", p.identity));
  room.on('participantDisconnected', p => log("participantDisconnected:", p.identity));
  room.on('disconnected', () => log("Disconnected."));
  room.on('trackSubscribed', (track, pub, participant) => {{
    if (track.kind === 'audio') {{
      const el = track.attach(); el.autoplay = true; el.playsInline = true; el.play().catch(()=>{{}});
      document.body.appendChild(el);
      log("Remote audio attached from", participant.identity || "peer");
    }}
  }});

  // Buttons
  document.getElementById('startAudioBtn').onclick = () => {{
    try {{
      const A = new Audio();
      A.src = "data:audio/mp3;base64,//uQZAAAAAAAAAAAAAAAAAAAA"; // tiny silent
      A.play().catch(()=>{{}});
      log("StartAudio request sent (to satisfy browser gesture).");
    }} catch (e) {{ log("StartAudio failed:", String(e)); }}
  }};

  document.getElementById('muteBtn').onclick = async () => {{
    try {{
      const was = room.localParticipant.isMicrophoneEnabled;  // property
      const now = await room.localParticipant.setMicrophoneEnabled(!was);
      badgeMic.textContent = now ? "Mic ON" : "Mic OFF";
      log(now ? "Mic ON" : "Mic OFF");
    }} catch (e) {{ log("Mic toggle failed:", String(e)); }}
  }};

  document.getElementById('leaveBtn').onclick = () => {{
    try {{ room.disconnect(); log("Disconnected"); }} catch (e) {{ log("Leave failed:", String(e)); }}
  }};

  // Connect
  const url = {json.dumps(info["url"])};
  const token = {json.dumps(info["token"])};
  try {{
    await room.connect(url, token);
    badgeConn.textContent = "Connected";
    log("Connected. Mic is OFF by default — click Toggle Mic to speak.");
  }} catch (e) {{
    badgeConn.textContent = "Connection failed";
    log("Connection failed:", String(e));
  }}
}})();
</script>
</body>
</html>
"""
    st.components.v1.html(html, height=640, scrolling=True)

st.divider()

# ---------- Talk to Grok (text -> spoken reply) ----------
st.subheader("🧠 Talk to Grok (quick demo)")
user_msg = st.text_area(
    "Say (or paste) something for Grok",
    height=80,
    placeholder="e.g., Summarize what GMF Builder does in 3 bullets."
)

col_a, col_b = st.columns([1, 1])
with col_a:
    speak_btn = st.button("Send to Grok → Speak reply", type="primary", use_container_width=True)
with col_b:
    just_text_btn = st.button("Send to Grok (text only)", use_container_width=True)

def _send_to_grok_and_show(prompt: str, speak: bool) -> None:
    if not prompt.strip():
        st.warning("Type something first.")
        return
    try:
        reply = tools.grok_chat(prompt.strip())
        st.success("Grok reply")
        st.write(reply)

        # best-effort log to n8n (ignore failures)
        try:
            tools.n8n_post("voice_demo_grok", {"prompt": prompt.strip(), "reply": reply})
        except Exception:
            pass

        if speak:
            # Speak in browser (no extra APIs; Web Speech API)
            st.components.v1.html(f"""
<script>
  try {{
    const text = {json.dumps(reply)};
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.03; u.pitch = 1.0; u.lang = 'en-US';
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  }} catch (e) {{
    console.log("Speech synthesis failed:", e);
  }}
</script>
""", height=1)
    except Exception as e:
        st.error(f"Grok error: {e}")

if speak_btn:
    _send_to_grok_and_show(user_msg, speak=True)
elif just_text_btn:
    _send_to_grok_and_show(user_msg, speak=False)

st.caption("Tip: keep this page open while talking. Mic is OFF until you click Toggle Mic.")