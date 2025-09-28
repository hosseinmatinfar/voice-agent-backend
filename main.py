# main.py
import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# ---- Env & defaults ---------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in Render environment variables")

REALTIME_MODEL = os.getenv("REALTIME_MODEL", "gpt-4o-realtime-preview-2024-12-17")
REALTIME_VOICE = os.getenv("REALTIME_VOICE", "alloy")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]

# ---- FastAPI app ------------------------------------------------------------
app = FastAPI(title="Mia Realtime Token Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Health -----------------------------------------------------------------
@app.get("/")
def health():
    return {"status": "ok"}


# ---- Realtime client_secret (WebRTC) ----------------------------------------
@app.post("/session")
async def create_ephemeral_session():
    """
    Create OpenAI Realtime client_secret for WebRTC.
    IMPORTANT: Fields MUST be top-level (no 'session' object).
    """
    url = "https://api.openai.com/v1/realtime/client_secrets"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    # Keep body minimal & valid for the endpoint
    body = {
        "model": REALTIME_MODEL,
        "voice": REALTIME_VOICE,
        "expires_after": 60  # seconds
        # اگر لازم شد می‌تونی بعداً اینا رو اضافه کنی:
        # "modalities": ["text", "audio"],
        # "audio_format": "wav",
        # توجه: خیلی از گزینه‌ها در client_secrets مجاز نیستند؛
        # اگر خطا گرفتی، حداقلِ لازم (model/voice/expires_after) را نگه دار.
    }

    print(">>> POST /client_secrets body:", json.dumps(body))

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, headers=headers, json=body)

    if resp.status_code >= 400:
        # Log error details from OpenAI
        try:
            detail = resp.json()
        except Exception:
            detail = {"raw": resp.text}
        print("<<< OpenAI error:", json.dumps(detail))
        raise HTTPException(status_code=500, detail=detail)

    data = resp.json()
    print("<<< OK: client_secret issued")
    return data


# ---- Local run (Render sets PORT) -------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
