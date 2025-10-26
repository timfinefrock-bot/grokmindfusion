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
    :root {{{{ --bg:#0b0e12; --panel:#10151c; --line:#1f2630; --text:#e8f0fe; --muted:#93a1b5; --good:#14c184; --bad:#f26d6d; --accent:#1f6feb; }}}}
    body{{{{margin:0;padding:24px;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;font-size:16px}}}}
    h2{{{{margin:0 0 12px}}}}
    .wrap{{{{max-width:980px;margin:0 auto}}}}
    .row{{{{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}}}}
    .pill{{{{display:inline-block;padding:6px 10px;border-radius:999px;border:1px solid var(--line);background:#0f1520;color:var(--muted);font-weight:600;font-size:13px}}}}
    .pill.good{{{{color:#c6ffea;border-color:#0b3a2f;background:#0c1f1a}}}}
    .pill.bad{{{{color:#ffe0e0;border-color:#432222;background:#1c0f0f}}}}
    button{{{{padding:12px 16px;border:0;border-radius:12px;background:var(--accent);color:#fff;cursor:pointer;font-weight:700}}}}
    button.secondary{{{{background:#263041}}}}
    .card{{{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;margin-top:16px}}}}
    #status{{{{white-space:pre-wrap;line-height:1.45;font-size:15px;color:#cfe;max-height:300px;overflow:auto;margin-top:10px}}}}
    .hint{{{{margin-top:12px;color:var(--muted);font-size:13px}}}}
  </style>
</head>
<body>
<div class="wrap">
  <h2>LiveKit Room: {room}</h2>
  <div class="row">
    <span id="connPill" class="pill bad">Disconnected</span>
    <span id="micPill"  class="pill">Mic OFF</span>
    <a id="openSecond" class="pill" style="text-decoration:none;cursor:pointer" title="Open this page in a new tab to join as another participant">+ open second tab</a>
  </div>
  <div class="card">
    <div class="row">
      <button id="muteBtn">🎙️ Toggle Mic</button>
      <button id="leaveBtn" class="secondary">🚪 Leave</button>
    </div>
    <div id="status">Loading LiveKit client…</div>
    <div class="hint">Tip: you won’t hear your own voice. Open this page on another device/tab with a different identity to hear each other.</div>
  </div>
</div>

<script>
(async () => {{
  const status   = document.getElementById('status');
  const connPill = document.getElementById('connPill');
  const micPill  = document.getElementById('micPill');
  const log = (...a) => {{
    console.log(...a);
    status.textContent += "\\n" + a.join(" ");
    status.scrollTop = status.scrollHeight;
  }};
  document.getElementById('openSecond').onclick = () => {{
    const url = new URL(window.location.href);
    url.searchParams.set('identity', 'user-' + Math.random().toString(16).slice(2,8));
    window.open(url.toString(), '_blank');
  }};

  // Prefer UMD global; fallback to ESM dynamic import.
  const UMD = [
    "https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js",
    "https://unpkg.com/livekit-client@2/dist/livekit-client.umd.min.js",
  ];
  const ESM = [
    "https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.esm.js",
    "https://unpkg.com/livekit-client@2/dist/livekit-client.esm.js",
    "https://esm.sh/livekit-client@2",
  ];

  function loadScript(src) {{
    return new Promise((resolve, reject) => {{
      const s = document.createElement('script');
      s.src = src; s.async = true;
      s.onload = () => resolve(src);
      s.onerror = () => reject(new Error("script failed: " + src));
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
    connPill.classList.toggle('good', ok);
    connPill.classList.toggle('bad', !ok);
  }};
  const setMic = (on) => {{
    micPill.textContent = on ? "Mic ON" : "Mic OFF";
    micPill.classList.toggle('good', on);
    micPill.classList.toggle('bad', false);
  }};

  room.on('participantConnected',   p => log("participantConnected:", p.identity));
  room.on('participantDisconnected',p => log("participantDisconnected:", p.identity));
  room.on('disconnected',           () => {{ setConn(false); log("Disconnected."); }});
  room.on('trackSubscribed', (track, pub, participant) => {{
    if (track.kind === 'audio') {{
      const el = track.attach(); el.autoplay = true; el.playsInline = true;
      el.play().catch(()=>{{}}); document.body.appendChild(el);
      log("Remote audio attached from", participant.identity || "peer");
    }}
  }});

  document.getElementById('muteBtn').onclick = async () => {{
    try {{
      const was = room.localParticipant.isMicrophoneEnabled; // property in v2
      const now = await room.localParticipant.setMicrophoneEnabled(!was);
      setMic(now); log(now ? "Mic ON" : "Mic OFF");
    }} catch (e) {{ log("Mic toggle failed: " + String(e)); }}
  }};
  document.getElementById('leaveBtn').onclick = () => {{
    try {{ room.disconnect(); setConn(false); log("Disconnected"); }}
    catch (e) {{ log("Leave failed: " + String(e)); }}
  }};

  const url   = {json.dumps(info["url"])};
  const token = {json.dumps(info["token"])};

  try {{
    await room.connect(url, token);
    setConn(true);
    setMic(false);
    log("Connected. Mic is OFF by default — click Toggle Mic to speak.");
  }} catch (e) {{
    setConn(false);
    log("Connection failed: " + String(e));
  }}
}})();
</script>
</body>
</html>
"""
    st.components.v1.html(html, height=620, scrolling=True)

st.caption("Tip: keep this page open while talking. Mic is OFF until you click Toggle Mic.")