# pages/Voice Mode (LiveKit).py
from __future__ import annotations

import json
import streamlit as st
import tools

st.set_page_config(page_title="Voice Mode (LiveKit)", layout="centered")
st.title("🎙️ Voice Mode (LiveKit)")

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

if st.button("🚀 Launch Voice (inline)"):
    try:
        info = tools.livekit_token(
            room.strip() or "mindfusion",
            identity.strip() or "user",
            name=identity.strip() or "user",
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
    --bg:#0a0b0e; --panel:#0f1115; --line:#2a2f39;
    --text:#ffffff; --muted:#d3d8e2; --ok:#19c08b; --warn:#ffb020; --err:#ff6b6b;
    --accent:#4f7cff;
  }}
  html,body {{ background:var(--bg); color:var(--text); font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif; margin:0; }}
  .wrap {{ max-width:980px; margin:0 auto; padding:24px; }}
  h2 {{ margin:0 0 12px; font-size:28px; }}
  .row {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
  .pill {{ padding:6px 12px; border-radius:999px; border:1px solid var(--line); background:#131722; font-weight:700; font-size:14px; }}
  .pill.ok {{ background:#0c1d16; border-color:#133a2c; color:#bbf7e0; }}
  .pill.err{{ background:#2a1212; border-color:#4a1e1e; color:#ffd6d6; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:16px; margin-top:16px; }}
  button {{ padding:12px 16px; border:0; border-radius:12px; background:var(--accent); color:#fff; font-weight:800; cursor:pointer; }}
  button.secondary {{ background:#2b3344; }}
  button.ghost {{ background:transparent; border:1px solid var(--line); color:#fff; }}
  #status {{ white-space:pre-wrap; font-size:15px; color:#e8f6ff; background:#0b0f17; border:1px solid #1e2530; border-radius:10px; padding:12px; max-height:320px; overflow:auto; }}
  .hint {{ margin-top:8px; color:var(--muted); font-size:14px; }}
</style>
</head>
<body>
<div class="wrap">
  <h2>LiveKit Room: {room}</h2>
  <div class="row" style="margin-bottom:10px">
    <span id="connPill" class="pill err">Disconnected</span>
    <span id="micPill"  class="pill">Mic OFF</span>
    <span id="subsPill" class="pill">Subscribing…</span>
  </div>

  <div class="card">
    <div class="row">
      <button id="startAudioBtn" class="ghost">🔓 Start Audio (if muted by browser)</button>
      <button id="muteBtn">🎙️ Toggle Mic</button>
      <button id="leaveBtn" class="secondary">🚪 Leave</button>
      <button id="monitorBtn" class="secondary">👂 Local Monitor</button>
    </div>
    <div id="status">Loading LiveKit client…</div>
    <div class="hint">
      You won’t hear your own voice. Open this page on another device/tab with a different identity to hear each other.
      If you see no audio, click <b>Start Audio</b> to satisfy the browser’s gesture requirement (iOS/Safari).
    </div>
  </div>
</div>

<script>
(async () => {{
  const status   = document.getElementById('status');
  const connPill = document.getElementById('connPill');
  const micPill  = document.getElementById('micPill');
  const subsPill = document.getElementById('subsPill');
  const log = (...a) => {{
    console.log(...a);
    status.textContent += "\\n" + a.join(" ");
    status.scrollTop = status.scrollHeight;
  }};

  // Load client: UMD first, then ESM fallback
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
      const s = document.createElement('script'); s.src = src; s.async = true;
      s.onload = () => resolve(src); s.onerror = () => reject(new Error("script failed: " + src));
      document.head.appendChild(s);
    }});
  }}

  async function tryUMD() {{
    for (const u of UMD) {{
      try {{
        await loadScript(u);
        if (window.LiveKit && window.LiveKit.Room) {{ log("UMD loaded:", u); return window.LiveKit; }}
      }} catch (e) {{ log("UMD error:", String(e)); }}
    }}
    return null;
  }}
  async function tryESM() {{
    for (const u of ESM) {{
      try {{ const m = await import(/* @vite-ignore */ u); log("ESM loaded:", u); return m; }}
      catch (e) {{ log("ESM error:", String(e)); }}
    }}
    return null;
  }}

  let LK = await tryUMD(); if (!LK) LK = await tryESM();
  if (!LK) {{ log("ERROR: LiveKit failed to load from CDNs."); return; }}

  const Room = LK.Room;
  const room = new Room({{ adaptiveStream: true, dynacast: true, publishDefaults: {{ dtx: true }} }});
  window.__lkRoom = room;

  const setConn = (ok) => {{
    connPill.textContent = ok ? "Connected" : "Disconnected";
    connPill.classList.toggle('ok', ok);
    connPill.classList.toggle('err', !ok);
  }};
  const setMic = (on) => {{
    micPill.textContent = on ? "Mic ON" : "Mic OFF";
    micPill.classList.toggle('ok', on);
    micPill.classList.toggle('err', false);
  }};
  const setSub = (txt) => {{ subsPill.textContent = txt; }};

  // Remote audio
  room.on('trackSubscribed', (track, pub, participant) => {{
    if (track.kind === 'audio') {{
      const el = track.attach(); el.autoplay = true; el.playsInline = true;
      el.play().catch(()=>{{}}); document.body.appendChild(el);
      setSub("Subscribed to " + (participant.identity || "peer"));
      log("Remote audio attached from", participant.identity || "peer");
    }}
  }});

  room.on('participantConnected',    p => log("participantConnected:", p.identity));
  room.on('participantDisconnected', p => log("participantDisconnected:", p.identity));
  room.on('disconnected',            () => {{ setConn(false); log("Disconnected."); }});

  // Buttons
  document.getElementById('startAudioBtn').onclick = async () => {{
    try {{
      if (room.startAudio) {{ await room.startAudio(); }}
      log("Audio context started.");
    }} catch (e) {{ log("Start Audio failed:", String(e)); }}
  }};

  document.getElementById('muteBtn').onclick = async () => {{
    try {{
      const was = room.localParticipant.isMicrophoneEnabled; // property in v2
      const now = await room.localParticipant.setMicrophoneEnabled(!was);
      setMic(now); log(now ? "Mic ON" : "Mic OFF");
    }} catch (e) {{ log("Mic toggle failed:", String(e)); }}
  }};

  document.getElementById('leaveBtn').onclick = () => {{
    try {{ room.disconnect(); setConn(false); log("Disconnected"); }}
    catch (e) {{ log("Leave failed:", String(e)); }}
  }};

  // Local monitor (optional, quiet loopback so you can hear *something*)
  let monitorNode = null;
  document.getElementById('monitorBtn').onclick = async () => {{
    try {{
      if (!monitorNode) {{
        const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const src = ctx.createMediaStreamSource(stream);
        const gain = ctx.createGain(); gain.gain.value = 0.15; // gentle
        src.connect(gain).connect(ctx.destination);
        monitorNode = {{ ctx, stream }};
        log("Local monitor ON (quiet).");
      }} else {{
        monitorNode.stream.getTracks().forEach(t => t.stop());
        monitorNode.ctx.close();
        monitorNode = null;
        log("Local monitor OFF.");
      }}
    }} catch (e) {{ log("Monitor failed:", String(e)); }}
  }};

  // Connect
  const url   = {json.dumps(info["url"])};
  const token = {json.dumps(info["token"])};

  try {{
    await room.connect(url, token);
    setConn(true); setMic(false); setSub("Waiting for peers…");
    log("Connected. Mic is OFF by default — click Toggle Mic to speak.");
  }} catch (e) {{
    setConn(false); log("Connection failed:", String(e));
  }}
}})();
</script>
</body>
</html>
"""
    st.components.v1.html(html, height=680, scrolling=True)

st.caption("Tip: keep this page open while talking. If you hear nothing, click ‘Start Audio’, then try again.")