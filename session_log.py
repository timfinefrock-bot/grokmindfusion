# ---------------------------
# Session logger (robust import + shims)
# ---------------------------
import time, uuid
try:
    import session_log as slog
    HAVE_SLOG = True
except Exception:
    HAVE_SLOG = False
    class slog:  # shims
        @staticmethod
        def start_session(**kw): return f"sess-{uuid.uuid4().hex[:8]}"
        @staticmethod
        def log_event(_sid, _evt, **_data): pass
        @staticmethod
        def flush_events(_sid): pass

def _ensure_session():
    if "gmf_session" in st.session_state and "gmf_session_id" in st.session_state:
        return
    # call start_session with kwargs that any version should ignore/safely accept
    sess = slog.start_session(app="gmf", page="voice_mode",
                              ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    # normalize to dict+id
    if isinstance(sess, dict):
        sid = sess.get("id") or sess.get("session") or f"sess-{uuid.uuid4().hex[:8]}"
        st.session_state.gmf_session = {**sess, "id": sid}
        st.session_state.gmf_session_id = sid
    else:
        sid = str(sess)
        st.session_state.gmf_session = {"id": sid, "ts": int(time.time())}
        st.session_state.gmf_session_id = sid

_ensure_session()
SESSION     = st.session_state.gmf_session      # dict
SESSION_ID  = st.session_state.gmf_session_id   # string

def log_event_safe(event: str, **data):
    try: slog.log_event(SESSION_ID, event, **data)
    except Exception: pass

def flush_events_safe():
    try: slog.flush_events(SESSION_ID)
    except Exception: pass