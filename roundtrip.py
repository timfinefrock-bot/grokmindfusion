# roundtrip.py — offline voice -> Grok -> voice demo
# Uses: AssemblyAI (STT), xAI Grok (reasoning), macOS 'say' (TTS), n8n (log)

import json
import subprocess
import sys
from pathlib import Path

import tools
import voice

AUDIO_IN = Path("test.aiff")  # change to your file if needed

def mac_say(text: str):
    """Speak text using macOS built-in TTS (safe + offline)."""
    try:
        subprocess.run(["say", text], check=True)
    except Exception as e:
        print(f"(warn) say failed: {e}")

def main():
    if not AUDIO_IN.exists():
        print(f"(error) input file not found: {AUDIO_IN.resolve()}")
        sys.exit(1)

    print("1) Transcribing audio…")
    tr = voice.transcribe_file(str(AUDIO_IN))
    if "error" in tr:
        print("AssemblyAI error:", tr["error"])
        sys.exit(2)

    text = tr.get("text", "").strip()
    conf = tr.get("confidence")
    print("   transcript:", text)
    print("   confidence:", conf)

    print("\n2) Asking Grok for a concise reply…")
    prompt = f"You are Mind Fusion. Reply concisely to: {text}"
    try:
        reply = tools.grok_chat(prompt)
    except Exception as e:
        print("Grok error:", e)
        sys.exit(3)

    print("   grok reply:", reply)

    print("\n3) Speaking the reply…")
    mac_say(reply)

    print("\n4) Posting event to n8n…")
    try:
        res = tools.n8n_post("fusion_roundtrip", {"input_text": text, "reply": reply, "stt_conf": conf})
        print("   n8n response:", json.dumps(res))
    except Exception as e:
        print("   n8n post failed:", e)

    print("\n✅ Round-trip complete.")

if __name__ == "__main__":
    main()