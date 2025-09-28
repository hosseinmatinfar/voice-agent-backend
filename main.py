# main.py
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# --- Env ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in Render environment variables")

DEFAULT_VOICE = os.getenv("REALTIME_VOICE", "alloy")  # optional

# --- App ---
app = FastAPI(title="Mia Realtime Token Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # در تولید محدودش کن
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/session")
async def create_ephemeral_session():
    """
    Create ephemeral client secret for OpenAI Realtime (WebRTC).
    NOTE: Do NOT send 'model' here. Model is set when posting SDP (?model=...).
    """
    url = "https://api.openai.com/v1/realtime/client_secrets"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "expires_after": {"seconds": 60},
        "session": {
            "type": "realtime",
            "voice": DEFAULT_VOICE,
            "instructions": (
                "You are Mia, a concise, helpful voice assistant. "
                "Respond in the user's language."
            ),
            # اختیاری‌ها:
            # "turn_detection": {"type": "server_vad"},
            # "modalities": ["text", "audio"],
        },
    }

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, headers=headers, json=body)

    if r.status_code >= 400:
        # خطای OpenAI را شفاف پاس بده به کلاینت
        try:
            detail = r.json()
        except Exception:
            detail = {"error": r.text}
        raise HTTPException(status_code=500, detail=detail)

    return r.json()
