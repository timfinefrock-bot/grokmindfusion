# pages/Voice Mode (LiveKit).py
from __future__ import annotations
import streamlit as st
import json
import tools  # uses your existing livekit_token()

st.set_page_config(page_title="Voice Mode (LiveKit)", layout="centered")
st.title("🎙️ Voice Mode (LiveKit)")

room = st.text_input("Room name", value="mindfusion")
identity = st.text_input("Your identity", value="user")

with st.expander("Environment (debug)"):
    LIVEKIT_URL = st.secrets.get("LIVEKIT_URL", "wss://cloud.livekit.io")
    LIVEKIT_API_KEY = st.secrets.get("LIVEKIT_API_KEY")
    LIVEKIT_API_SECRET = st.secrets.get("LIVEKIT_API_SECRET")
    st.code(
        "\n".join(
            [
                f"LIVEKIT_URL: {LIVEKIT_URL}",
                f"LIVEKIT_API_KEY: {LIVEKIT_API_KEY[:4]+'…'+LIVEKIT_API_KEY[-4:] if LIVEKIT_API_KEY else '—'}",
                f"LIVEKIT_API_SECRET: {LIVEKIT_API_SECRET[:4]+'…'+LIVEKIT_API_SECRET[-4:] if LIVEKIT_API_SECRET else '—'}",
            ]
        ),
        language="bash",
    )

if st.button("🚀 Launch Voice (inline)"):
    try:
        info = tools.livekit_token(room.strip() or "mindfusion", identity.strip() or "user", name=identity.strip() or "user")
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
    body{{margin:0;padding:20px;background:#0b0e12;color:#e8f0fe;font-family:system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif}}
    .wrap{{max-width:840px;margin:0 auto}}
    .row{{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}}
    button{{padding:10px 14px;border:0;border-radius:10px;background:#1f6feb;color:#fff;cursor:pointer}}
    #status{{margin-top:8px;white-space:pre-wrap;font-size:14px;line-height:1.35}}
    .card{{background:#10151c;border:1px solid #1f2630;border-radius:12px;padding:16px;margin-top:16px}}
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
    <div id="status">Loading LiveKit…</div>
  </div>
</div>

<script>
(async () => {{
  const logEl = document.getElementById('status');
  const log = (...a) => {{
    console.log(...a);
    logEl.textContent = a.map(x => (typeof x === 'string' ? x : JSON.stringify(x))).join(' ');
  }};
  const append = (...a) => {{
    console.log(...a);
    logEl.textContent += "\\n" + a.map(x => (typeof x === 'string' ? x : JSON.stringify(x))).join(' ');
  }};

  // 1) Try UMD global first (fast path)
  try {{
    await new Promise((resolve, reject) => {{
      const s = document.createElement('script');
      s.src = "https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js";
      s.onload = resolve;
      s.onerror = () => reject(new Error('UMD script failed to load'));
      document.head.appendChild(s);
    }});
  }} catch (e) {{
    append('UMD load error:', String(e));
  }}

  let Room, createLocalAudioTrack;

  if (window.LiveKit && window.LiveKit.Room) {{
    // UMD path
    ;({{ Room, createLocalAudioTrack }} = window.LiveKit);
    append('LiveKit UMD loaded.');
  }} else {{
    // 2) Fallback: ESM dynamic import
    try {{
      const mod = await import('https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.esm.js');
      Room = mod.Room;
      createLocalAudioTrack = mod.createLocalAudioTrack;
      append('LiveKit ESM loaded.');
    }} catch (e) {{
      log('ERROR: LiveKit failed to load (UMD & ESM).');
      append('Details:', String(e));
      return;
    }}
  }}

  const url = {json.dumps(info["url"])};
  const token = {json.dumps(info["token"])};

  const room = new Room({{
    adaptiveStream: true,
    dynacast: true,
    publishDefaults: {{ dtx: true }},
    // leave playback to user gesture toggle
  }});
  window.__lkRoom = room;

  room.on('participantConnected', p => append('participantConnected:', p.identity));
  room.on('participantDisconnected', p => append('participantDisconnected:', p.identity));
  room.on('disconnected',       () => append('Disconnected.'));
  room.on('trackSubscribed', (track, pub, participant) => {{
    if (track.kind === 'audio') {{
      const el = track.attach();
      el.autoplay = true; el.playsInline = true;
      el.play().catch(()=>{{}});
      document.body.appendChild(el);
      append('Remote audio attached from', participant.identity || 'peer');
    }}
  }});

  document.getElementById('muteBtn').onclick = async () => {{
    try {{
      const was = room.localParticipant.isMicrophoneEnabled();
      const now = await room.localParticipant.setMicrophoneEnabled(!was);
      append(now ? 'Mic ON' : 'Mic OFF');
    }} catch (e) {{
      append('Mic toggle failed:', String(e));
    }}
  }};
  document.getElementById('leaveBtn').onclick = () => {{
    try {{ room.disconnect(); }} catch (e) {{ append('Leave failed:', String(e)); }}
  }};

  try {{
    await room.connect(url, token);
    append('Connected. Mic is OFF by default — click Toggle Mic to speak.');
  }} catch (e) {{
    log('Connection failed:', String(e));
    return;
  }}
}})();
</script>
</body>
</html>
"""
    st.components.v1.html(html, height=540, scrolling=True)

st.caption("Tip: keep this page open while talking. Mic is OFF until you click Toggle Mic.")