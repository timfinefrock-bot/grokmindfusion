# session_log.py — persistent logging for GrokMind Fusion sessions
import os, time, json, sqlite3, requests

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "gmf.db")
N8N_LOG_URL = os.getenv("N8N_LOG_URL", "")  # optional webhook for Dropbox mirror

def _conn():
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, session TEXT, event TEXT, data TEXT
    )""")
    return con

def start_session(**meta):
    return {"id": f"sess-{int(time.time())}", "ts": int(time.time()), "meta": meta}

def log_event(session: dict, event: str, **data):
    con = _conn()
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    con.execute("INSERT INTO events(ts,session,event,data) VALUES(?,?,?,?)",
                (ts, session["id"], event, json.dumps(data)))
    con.commit()
    if N8N_LOG_URL:
        try:
            payload = {"ts": ts, "session": session["id"], "event": event, "data": data}
            requests.post(N8N_LOG_URL, json=payload, timeout=5)
        except Exception:
            pass  # network errors ignored for safety

def flush_events(session: dict):
    # no-op placeholder for future batching
    pass