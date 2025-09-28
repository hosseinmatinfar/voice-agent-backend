# app.py
import os, json
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in Render env vars")

# مدل Realtime پیشنهادی (می‌تونی بعداً عوضش کنی)
REALTIME_MODEL = os.getenv("REALTIME_MODEL", "gpt-4o-realtime-preview")

# صدای پیش‌فرض (اسم‌های متداول: alloy, verse, aria, breeze ...)
DEFAULT_VOICE = os.getenv("REALTIME_VOICE", "alloy")

app = FastAPI()

# برای موبایل/وب
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
    روی OpenAI، یک client_secret کوتاه‌عمر می‌سازیم
    طبق داک GA: POST /v1/realtime/client_secrets
    """
    url = "https://api.openai.com/v1/realtime/client_secrets"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": REALTIME_MODEL,
        # مدت اعتبار کوتاه؛ می‌تونی کم/زیادش کنی
        "expires_after": {"seconds": 60},
        # تنظیمات اولیه‌ی سشن (اختیاری ولی مفید)
        "voice": DEFAULT_VOICE,
        "instructions": "You are Mia, a concise, helpful voice assistant. Answer in the user's language.",
        # اگر transcription هم می‌خواهی:
        # "input_audio_format": "webrtc",  # برای WebRTC لازم نیست ست کنی
        # "output_audio_format": "webrtc",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, headers=headers, json=body)
    if r.status_code >= 400:
        try:
            err = r.json()
        except Exception:
            err = {"error": r.text}
        raise HTTPException(status_code=500, detail=err)

    return r.json()
