# app.py (Render)
import os, httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY")

DEFAULT_VOICE = os.getenv("REALTIME_VOICE", "alloy")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # در محصولی محدودش کن
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
    Create ephemeral client secret for WebRTC Realtime.
    NOTE: Do NOT send 'model' here. Model is set on the SDP POST (?model=...).
    """
    url = "https://api.openai.com/v1/realtime/client_secrets"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        # "model": "gpt-4o-realtime-preview",  # ❌ نذار
        "expires_after": {"seconds": 60},
        "session": {                     # ✅ همه تنظیمات زیر session
            "type": "realtime",
            "voice": DEFAULT_VOICE,
            "instructions": (
                "You are Mia, a concise, helpful voice assistant. "
                "Respond in the user's language."
            ),
            
             "modalities": ["text","audio"],
            "turn_detection": {"type": "server_vad"},
        },
    }

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, headers=headers, json=body)

    if r.status_code >= 400:
        # پاسخ خطا را شفاف پاس بده به کلاینت
        raise HTTPException(status_code=500, detail=r.json())

    return r.json()
