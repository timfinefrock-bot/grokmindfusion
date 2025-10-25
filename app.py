# 2) dashboard.py (final base with Builder + LiveKit)
# dashboard.py — GrokMind Fusion Control Panel (final base)
# Status + Chat + Transcribe + n8n + LiveKit Realtime + Builder panel

import os
import uuid
import tempfile
from dotenv import load_dotenv
import streamlit as st
import tools
import voice

load_dotenv()
st.set_page_config(page_title="GrokMind Fusion", layout="centered")
st.title("🧠 GrokMind Fusion")

def masked(val: str, keep: int = 4) -> str:
    if not val: return "—"
    return (val[:keep] + "…" + val[-keep:]) if len(val) > keep*2 else "•••"

# ---- Environment ----
st.subheader("Environment")
xai = os.getenv("XAI_API_KEY")
aai = os.getenv("ASSEMBLYAI_API_KEY")
lk_key = os.getenv("LIVEKIT_API_KEY")
lk_sec = os.getenv("LIVEKIT_API_SECRET")
lk_url = os.getenv("LIVEKIT_URL") or "wss://cloud.livekit.io"
n8n = os.getenv("N8N_WORKSPACE_URL")
sl = os.getenv("STREAMLIT_ACCOUNT")

def check_row(label, value):
    ok = bool(value)
    st.write(("✅" if ok else "🟡"), f"**{label}**", f"`{masked(value)}`" if value else " (not set)")
    return ok

_ = [
    check_row("XAI_API_KEY", xai),
    check_row("ASSEMBLYAI_API_KEY", aai),
    check_row("LIVEKIT_API_KEY", lk_key),
    check_row("LIVEKIT_API_SECRET", lk_sec),
    check_row("LIVEKIT_URL", lk_url),
    check_row("N8N_WORKSPACE_URL", n8n),
    check_row("STREAMLIT_ACCOUNT", sl),
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
audio = st.file_uploader("Upload audio (aiff/wav/mp3/m4a)", type=["aiff","wav","mp3","m4a"])
auto_ask = st.checkbox("Ask Grok about the transcript", value=True)
log_n8n2 = st.checkbox("Post to n8n", value=True, key="log2")
if st.button("Transcribe", use_container_width=True, disabled=audio is None):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{audio.name}") as tmp:
            tmp.write(audio.getbuffer())
            tmp_path = tmp.name
        res = voice.transcribe_file(tmp_path)
        if "error" in res:
            st.error(f"AssemblyAI error: {res['error']}")
        else:
            txt = res.get("text","").strip()
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
                            tools.n8n_post("grok_reply_from_transcript",
                                           {"input_text": txt, "reply": reply, "stt_conf": res.get("confidence")})
                        except Exception as e:
                            st.warning(f"n8n post failed: {e}")
                except Exception as e:
                    st.error(f"Grok error: {e}")
    finally:
        try:
            if "tmp_path" in locals():
                os.remove(tmp_path)
        except Exception:
            pass

st.divider()

# ---- LiveKit Realtime (Join Room) ----
st.header("Realtime Voice (LiveKit)")
colA, colB = st.columns(2)
with colA:
    room = st.text_input("Room name", value="mindfusion")
with colB:
    identity = st.text_input("Your identity", value=f"user-{uuid.uuid4().hex[:6]}")
enabled = bool(lk_key and lk_sec and room.strip() and identity.strip())
if st.button("Join Live Voice (beta)", disabled=not enabled, use_container_width=True):
    try:
        info = tools.livekit_token(room.strip(), identity.strip(), name=identity.strip())
        html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>LiveKit Join</title>
<script src="https://unpkg.com/@livekit/client@2"></script>
<style>body {{ font-family: sans-serif; }} .btn {{ padding:8px 12px; margin:6px; }} #status {{ margin:8px 0; }}</style>
</head>
<body>
<h3>LiveKit Room: {room}</h3>
<div id="status">Connecting…</div>
<button class="btn" id="muteBtn">Toggle Mute</button>
<button class="btn" id="leaveBtn">Leave</button>
<script>
(async () => {{
  const url = "{info['url']}";
  const token = "{info['token']}";
  const room = new Livekit.Room();
  const connectOpts = {{ autoSubscribe: true }};
  room.on('participantConnected', p => console.log('participantConnected', p.identity));
  room.on('trackSubscribed', (track, pub, participant) => {{
    if (track.kind === 'audio') {{
      const el = track.attach(); document.body.appendChild(el);
    }}
  }});
  document.getElementById('muteBtn').onclick = async () => {{
    const enabled = await room.localParticipant.setMicrophoneEnabled(!(room.localParticipant.isMicrophoneEnabled));
    document.getElementById('status').innerText = enabled ? 'Mic ON' : 'Mic OFF';
  }};
  document.getElementById('leaveBtn').onclick = () => room.disconnect();
  try {{
    await room.connect(url, token, connectOpts);
    document.getElementById('status').innerText = 'Connected. Mic OFF by default—click Toggle Mute to speak.';
  }} catch (e) {{
    document.getElementById('status').innerText = 'Connection failed: ' + e;
  }}
}})();
</script>
</body>
</html>
"""
        st.components.v1.html(html, height=420)
        st.success("LiveKit client loaded. Use the buttons to mute/unmute and leave.")
    except Exception as e:
        st.error(f"LiveKit token failed: {e}")

st.divider()

# ---- Builder panel (sends structured spec to n8n) ----
st.header("Builder (send spec to n8n)")
spec = st.text_area("Describe what to build", placeholder="e.g., Online directory for dog grooming on Cape Cod with search by town, rating, and mobile-friendly UI.", height=140)
col1, col2 = st.columns(2)
with col1:
    priority = st.selectbox("Priority", ["low","normal","high"], index=1)
with col2:
    notes = st.text_input("Notes (optional)", placeholder="Design preferences, tech stack, etc.")
if st.button("Send Build Request", type="primary", use_container_width=True, disabled=not bool(spec.strip())):
    try:
        res = tools.builder_task(spec, priority=priority, notes=notes)
        st.success("Build request sent to n8n.")
        st.json(res)
    except Exception as e:
        st.error(f"Builder request failed: {e}")

st.divider()
st.caption("GrokMind Fusion — cloud app. Secrets are stored in Streamlit Secrets.")
