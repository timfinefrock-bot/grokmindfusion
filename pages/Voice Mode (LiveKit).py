# pages/Voice Mode (LiveKit).py
# Streamlit page that opens a full LiveKit voice client in a NEW TAB.

from __future__ import annotations

import os
import uuid
import json
import base64
import streamlit as st

# ------------ helpers ------------
def _secret(key: str, default: str | None = None) -> str | None:
    try:
        _ = st.secrets
        # type: ignore[attr-defined]
        return st.secrets.get(key, default)
    except Exception:
        return os.getenv(key, default)

def masked(val: str | None, keep: int = 4) -> str:
    if not val:
        return "—"
    return (val[:keep] + "…" + val[-keep:]) if len(val) > keep * 2 else "•••"

# ------------ config ------------
LIVEKIT_API_KEY = _secret("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = _secret("LIVEKIT_API_SECRET")
LIVEKIT_URL = _secret("LIVEKIT_URL") or "wss://cloud.livekit.io"

# We use tools.livekit_token just like the main app
import tools  # local module

st.set_page_config(page_title="Voice Mode (LiveKit)", layout="centered")
st.title("🎙️ Voice Mode (LiveKit)")

st.caption(
    "Click the button below to launch the LiveKit voice client in a new browser tab. "
    "Mic is OFF by default; toggle it in the new tab."
)

# UI: room + identity
col1, col2 = st.columns(2)
with col1:
    room = st.text_input("Room name", value="mindfusion")
with col2:
    identity = st.text_input("Your identity", value=f"user-{uuid.uuid4().hex[:6]}")

# Status block for secrets
with st.expander("Environment (debug)"):
    st.write("LIVEKIT_URL:", f"`{masked(LIVEKIT_URL)}`")
    st.write("LIVEKIT_API_KEY:", f"`{masked(LIVEKIT_API_KEY)}`")
    st.write("LIVEKIT_API_SECRET:", f"`{masked(LIVEKIT_API_SECRET)}`")

enabled = bool(LIVEKIT_API_KEY and LIVEKIT_API_SECRET and room.strip() and identity.strip())

# Build the popup HTML (written into new tab)
def make_livekit_html(url: str, token: str, room_name: str) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>LiveKit Voice — {room_name}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <!-- Use UMD build so window.LiveKit exists -->
  <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }}
    .row {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
    .btn {{ padding:10px 14px; border-radius:12px; border:1px solid #888; cursor:pointer; }}
    #status {{ margin:10px 0 16px 0; font-weight:600; }}
    .pill {{ padding:6px 10px; border-radius:999px; background:#eee; display:inline-block; margin-left:8px; }}
    audio {{ display:none; }}
  </style>
</head>
<body>
  <h2>LiveKit Room: {room_name} <span class="pill">Voice Mode</span></h2>
  <div id="status">Loading…</div>
  <div class="row">
    <button class="btn" id="muteBtn">🎙️ Toggle Mic</button>
    <button class="btn" id="leaveBtn">🚪 Leave</button>
  </div>

  <script>
  (async () => {{
    try {{
      if (!window.LiveKit || !window.LiveKit.Room) {{
        document.getElementById('status').innerText = 'LiveKit client failed to load.';
        return;
      }}

      const {{ Room }} = window.LiveKit;
      const room = new Room({{
        adaptiveStream: true,
        dynacast: true,
        publishDefaults: {{ dtx: true }}
      }});
      window.__lkRoom = room; // for console debugging

      room.on('trackSubscribed', (track) => {{
        if (track.kind === 'audio') {{
          const el = track.attach();
          el.autoplay = true;
          el.playsInline = true;
          el.play().catch(() => {{}});
          document.body.appendChild(el);
        }}
      }});

      room.on('participantConnected', (p) => console.log('participantConnected:', p.identity));
      room.on('participantDisconnected', (p) => console.log('participantDisconnected:', p.identity));

      document.getElementById('muteBtn').onclick = async () => {{
        try {{
          const was = room.localParticipant.isMicrophoneEnabled();
          const now = await room.localParticipant.setMicrophoneEnabled(!was);
          document.getElementById('status').innerText = now ? 'Mic ON' : 'Mic OFF';
        }} catch (e) {{
          console.error(e);
          document.getElementById('status').innerText = 'Mic toggle failed: ' + e;
        }}
      }};

      document.getElementById('leaveBtn').onclick = () => {{
        try {{
          room.disconnect();
          document.getElementById('status').innerText = 'Disconnected';
        }} catch (e) {{
          console.error(e);
          document.getElementById('status').innerText = 'Leave failed: ' + e;
        }}
      }};

      document.getElementById('status').innerText = 'Connecting…';
      await room.connect("{url}", "{token}");
      document.getElementById('status').innerText =
        'Connected. Mic is OFF by default — click “Toggle Mic” to speak.';
    }} catch (err) {{
      console.error(err);
      document.getElementById('status').innerText = 'Connection failed: ' + err;
    }}
  }})();
  </script>
</body>
</html>"""

if st.button("🚀 Launch Voice Mode (opens in new tab)", type="primary", disabled=not enabled, use_container_width=True):
    try:
        info = tools.livekit_token(room.strip(), identity.strip(), name=identity.strip())
        html = make_livekit_html(info["url"], info["token"], room.strip())

        # Open a new tab and write the HTML into it (data carried via base64 to avoid quoting issues)
        b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")
        popup = f"""
<!doctype html>
<html>
  <body>
    <script>
      (function() {{
        const html = atob("{b64}");
        const w = window.open("", "_blank");
        if (!w) {{
          alert("Popup blocked — please allow popups for this site and try again.");
          return;
        }}
        w.document.open();
        w.document.write(html);
        w.document.close();
      }})();
    </script>
    <p>Opening Voice Mode… If nothing appears, enable popups and click again.</p>
  </body>
</html>
"""
        st.components.v1.html(popup, height=100)
        st.success("Voice Mode opened in a new tab. If you don’t see it, enable popups and click again.")
    except Exception as e:
        st.error(f"LiveKit token failed: {e}")