# voice.py — Mind Fusion voice helpers
# STT: AssemblyAI (works today)
# TTS: macOS 'say' (temporary, simple & offline). We can swap to a cloud TTS later.

import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

import assemblyai as aai

load_dotenv()

def _aai_ready():
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise RuntimeError("ASSEMBLYAI_API_KEY is not set in .env")
    aai.settings.api_key = api_key

# -------- STT --------
def transcribe_file(path: str) -> dict:
    """
    Transcribe a local audio file (wav/mp3/m4a/aiff etc.) with AssemblyAI.
    Returns: {text, confidence, words[]} or {error}
    """
    _aai_ready()
    transcriber = aai.Transcriber()
    try:
        transcript = transcriber.transcribe(path)

        if transcript.status == aai.TranscriptStatus.error:
            return {"error": transcript.error or "Unknown AssemblyAI error"}

        words = []
        if transcript.words:
            for w in transcript.words:
                words.append({
                    "text": w.text,
                    "start": getattr(w, "start", None),
                    "end": getattr(w, "end", None),
                    "confidence": getattr(w, "confidence", None),
                })
        return {
            "text": transcript.text or "",
            "confidence": getattr(transcript, "confidence", None),
            "words": words,
        }
    except Exception as e:
        return {"error": str(e)}

# -------- TTS (temporary: macOS 'say') --------
def tts_say(text: str):
    """Speak text out loud using macOS 'say' (no file saved)."""
    try:
        subprocess.run(["say", text], check=True)
    except Exception as e:
        print(f"(warn) say failed: {e}")

def tts_say_to_file(text: str, out_path: str = "reply.aiff") -> str:
    """Synthesize to an AIFF file using 'say -o'; returns the saved path."""
    p = Path(out_path)
    try:
        subprocess.run(["say", text, "-o", str(p)], check=True)
        return str(p)
    except Exception as e:
        raise RuntimeError(f"say-to-file failed: {e}")