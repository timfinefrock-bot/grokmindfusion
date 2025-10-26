# pages/Voice_Mode_(LiveKit).py
from __future__ import annotations

import os
import json
import streamlit as st
import tools  # uses your existing livekit_token()

st.set_page_config(page_title="Voice Mode (LiveKit)", layout="centered")
st.title("🎙️ Voice Mode (LiveKit)")

# Inputs (room / identity)
colA, colB = st.columns(2)
with colA:
    room = st.text_input("Room name", value="mindfusion")
with colB:
    identity = st.text_input("Your identity", value="user")

# Debug (optional)
with st.expander("Environment (debug)", expanded=False):
    st.write("LIVEKIT_URL:", os.getenv("LIVEKIT_URL"))
    st.write("LIVEKIT_API_KEY:", (os.getenv("LIVEKIT_API_KEY") or "")[:4] + "…")
    st.write("LIVEKIT_API_SECRET:", (os.getenv("LIVEKIT_API_SECRET") or "")[:4] + "…")

launch = st.button("🚀 Launch Voice (inline)")

if launch:
    try:
        info = tools.livekit_token(room.strip() or "mindfusion",
                                   identity.strip() or "user",
                                   name=identity.strip() or "user")

        # Minimal client using the UMD build (global window.LiveKit)
        html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Voice Mode</title>
  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
  <style>
    body {{
      margin: 0; padding: 24px; background:#0b0e12; color:#e7eef7;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    }}
    .row {{ display:flex; gap:12px; flex-wrap:wrap; margin:12px 0; }}
    button {{
      padding:10px 14px; border-radius:10px; background:#3b3f46; color:#fff; border:0; cursor:pointer;
    }}
    #status {{ margin-top:10px; font-size:14px; opacity:0.9; }}
    .tag {{ display:inline-block; background:#1f2530; padding:6px 12px; border-radius:16px; margin-left:12px; }}
  </style>
</head>
<body>
  <h2>LiveKit Room: {room}</h2>
  <span class="tag">Voice Mode</span>

  <div id="status">Connecting…</div>
  <div class="row">
    <button id="muteBtn">Toggle Mic</button>
    <button id="leaveBtn">Leave</button>
  </div>

  <script>
  (async () => {{
    if (!window.LiveKit) {{
      document.getElementById('status').innerText = 'LiveKit client failed to load.';
      return;
    }}

    const url = "{info['url']}";
    const token = "{info['token']}";
    const {{ Room }} = window.LiveKit;

    const room = new Room({{
      adaptiveStream: true,
      dynacast: true,
      publishDefaults: {{ dtx: true }},
    }});

    // Attach remote audio
    room.on('trackSubscribed', (track) => {{
      if (track.kind === 'audio') {{
        const el = track.attach();
        el.autoplay = true; el.playsInline = true;
        el.play().catch(() => {{ /* ignore */ }});
        document.body.appendChild(el);
      }}
    }});

    // Buttons
    document.getElementById('muteBtn').onclick = async () => {{
      try {{
        const on = room.localParticipant.isMicrophoneEnabled();
        const now = await room.localParticipant.setMicrophoneEnabled(!on);
        document.getElementById('status').innerText = now ? 'Mic ON' : 'Mic OFF';
      }} catch (e) {{
        document.getElementById('status').innerText = 'Mic toggle failed: ' + e;
        console.error(e);
      }}
    }};

    document.getElementById('leaveBtn').onclick = () => {{
      try {{ room.disconnect(); document.getElementById('status').innerText = 'Disconnected'; }}
      catch (e) {{ console.error(e); }}
    }};

    try {{
      await room.connect(url, token);
      document.getElementById('status').innerText =
        'Connected. Mic OFF by default — click Toggle Mic to speak.';
      // Do NOT auto-enable mic: user must click
    }} catch (e) {{
      console.error(e);
      document.getElementById('status').innerText = 'Connection failed: ' + e;
    }}
  }})();
  </script>
</body>
</html>
"""
        # Render inline (no data: URL; avoids CSP blockers)
        st.components.v1.html(html, height=520)

    except Exception as e:
        st.error(f"LiveKit token failed: {e}")

st.caption("Tip: keep this page open while talking. Mic is off until you click Toggle Mic.")