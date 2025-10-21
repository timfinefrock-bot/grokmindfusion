# dashboard.py — GrokMind Fusion Control Panel
# Status + Chat with Grok + Audio Transcribe + n8n logging
import os
import tempfile
from dotenv import load_dotenv
import streamlit as st

import tools
import voice

load_dotenv()

def masked(val: str, keep: int = 4) -> str:
    if not val:
        return "—"
    return (val[:keep] + "…" + val[-keep:]) if len(val) > keep*2 else "•••"

st.set_page_config(page_title="GrokMind Fusion", layout="centered")
st.title("🧠 GrokMind Fusion")

# ---- Status panel ----
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
    st.write(("✅" if ok else "🟡"), f"**{label}**",
             f"`{masked(value)}`" if value else " (not set)")
    return ok

all_ok = True
all_ok &= check_row("XAI_API_KEY", xai)
all_ok &= check_row("ASSEMBLYAI_API_KEY", aai)
all_ok &= check_row("LIVEKIT_API_KEY", lk_key)
all_ok &= check_row("LIVEKIT_API_SECRET", lk_sec)
check_row("LIVEKIT_URL", lk_url)
check_row("N8N_WORKSPACE_URL", n8n)
check_row("STREAMLIT_ACCOUNT", sl)

st.divider()

# session state
if "last_transcript" not in st.session_state:
    st.session_state.last_transcript = ""
if "last_reply" not in st.session_state:
    st.session_state.last_reply = ""

col1, col2 = st.columns(2, gap="large")

# ---- Chat with Grok ----
with col1:
    st.header("Chat with Grok")
    user_text = st.text_area("Your message", placeholder="Type a question or instruction…", height=120)
    speak = st.checkbox("Speak reply (macOS)", value=True)
    log_n8n = st.checkbox("Post to n8n", value=True)
    if st.button("Ask Grok", type="primary", use_container_width=True, disabled=not bool(user_text.strip())):
        try:
            reply = tools.grok_chat(user_text.strip())
            st.session_state.last_reply = reply
            st.success("Grok replied:")
            st.write(reply)
            if speak:
                try:
                    voice.tts_say(reply)
                except Exception as e:
                    st.warning(f"TTS speak failed: {e}")
            if log_n8n:
                try:
                    tools.n8n_post("grok_reply", {"prompt": user_text.strip(), "reply": reply})
                except Exception as e:
                    st.warning(f"n8n post failed: {e}")
        except Exception as e:
            st.error(f"Grok error: {e}")

# ---- Transcribe Audio ----
with col2:
    st.header("Transcribe Audio")
    audio = st.file_uploader("Upload audio (aiff/wav/mp3/m4a)", type=["aiff","wav","mp3","m4a"])
    auto_ask = st.checkbox("Ask Grok about the transcript", value=True)
    speak2 = st.checkbox("Speak Grok's answer (macOS)", value=True, key="speak2")
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
                st.session_state.last_transcript = txt
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
                        st.session_state.last_reply = reply
                        st.info("Grok reply:")
                        st.write(reply)
                        if speak2:
                            try:
                                voice.tts_say(reply)
                            except Exception as e:
                                st.warning(f"TTS speak failed: {e}")
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
st.caption("GrokMind Fusion — local dev. Secrets load from .env; production uses container envs.")