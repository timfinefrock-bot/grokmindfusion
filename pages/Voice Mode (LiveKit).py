# pages/Voice Mode (LiveKit).py
from __future__ import annotations
import streamlit as st
import json
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
        info = tools.livekit_token(room.strip() or "mindfusion",
                                   identity.strip() or "user",
                                   name=identity.strip() or "user")
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
    body{{margin:0;padding:20px;background:#0b0e12;color:#e8f0fe;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif}}
    .wrap{{max-width:860px;margin:0 auto}}
    .row{{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}}
    button{{padding:10px 14px;border:0;border-radius:10px;background:#1f6feb;color:#fff;cursor:pointer}}
    .card{{background:#10151c;border:1px solid #1f2630;border-radius:12px;padding:16px;margin-top:16px}}
    #status{{white-space:pre-wrap;line-height:1.35;font-size:14px}}
  </style>
</head>
<body>
<div class="wrap">
  <h2>LiveKit Room: {room}</h2>
  <div class="card">
    <div class="row">
      <button id="muteBtn">🎙️ Toggle Mic</button>
      <button id="leaveBtn">🚪 Leave</button>
    </div>
    <div id="status">Starting loader…</div>
  </div>
</div>

<script>
(async () => {{
  const status = document.getElementById('status');
  const log = (...a) => {{
    console.log(...a);
    status.textContent += "\\n" + a.join(" ");
  }};
  status.textContent = "Loading LiveKit client…";

  const UMD = [
    "https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js",
    "https://unpkg.com/livekit-client@2/dist/livekit-client.umd.min.js"
  ];
  const ESM = [
    "https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.esm.js",
    "https://unpkg.com/livekit-client@2/dist/livekit-client.esm.js"
  ];

  async function loadScript(src) {{
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
        if (window.LiveKit && window.LiveKit.Room) {{
          log("UMD loaded:", url);
          return window.LiveKit;
        }}
      }} catch (e) {{
        log("UMD error:", String(e));
      }}
    }}
    return null;
  }}

  async function tryESM() {{
    for (const url of ESM) {{
      try {{
        const mod = await import(/* @vite-ignore */ url);
        log("ESM loaded:", url);
        return mod;
      }} catch (e) {{
        log("ESM error:", String(e));
      }}
    }}
    return null;
  }}

  let LK = await tryUMD();
  if (!LK) LK = await tryESM();

  if (!LK) {{
    status.textContent = "ERROR: LiveKit failed to load from jsDelivr and unpkg (UMD & ESM).";
    return;
  }}

  const Room = LK.Room;
  const room = new Room({{
    adaptiveStream: true,
    dynacast: true,
    publishDefaults: {{ dtx: true }},
  }});
  window.__lkRoom = room;

  room.on('participantConnected', p => log("participantConnected:", p.identity));
  room.on('participantDisconnected', p => log("participantDisconnected:", p.identity));
  room.on('disconnected', () => log("Disconnected."));
  room.on('trackSubscribed', (track, pub, participant) => {{
    if (track.kind === 'audio') {{
      const el = track.attach();
      el.autoplay = true; el.playsInline = true;
      el.play().catch(()=>{{}});
      document.body.appendChild(el);
      log("Remote audio attached from", participant.identity || "peer");
    }}
  }});

  document.getElementById('muteBtn').onclick = async () => {{
    try {{
      const was = room.localParticipant.isMicrophoneEnabled();
      const now = await room.localParticipant.setMicrophoneEnabled(!was);
      log(now ? "Mic ON" : "Mic OFF");
    }} catch (e) {{ log("Mic toggle failed:", String(e)); }}
  }};
  document.getElementById('leaveBtn').onclick = () => {{
    try {{ room.disconnect(); }} catch (e) {{ log("Leave failed:", String(e)); }}
  }};

  const url = {json.dumps(info["url"])};
  const token = {json.dumps(info["token"])};

  try {{
    await room.connect(url, token);
    log("Connected. Mic is OFF by default — click Toggle Mic to speak.");
  }} catch (e) {{
    log("Connection failed:", String(e));
  }}
}})();
</script>
</body>
</html>
"""
    st.components.v1.html(html, height=560, scrolling=True)

st.caption("Tip: keep this page open while talking. Mic is OFF until you click Toggle Mic.")