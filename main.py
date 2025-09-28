# main.py
import os, json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in Render environment variables")

DEFAULT_VOICE = os.getenv("REALTIME_VOICE", "alloy")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]

app = FastAPI(title="Mia Realtime Token Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    - DO NOT send 'model' here (model is set in SDP POST query).
    - 'expires_after.anchor' must be 'created_at'.
    """
    url = "https://api.openai.com/v1/realtime/client_secrets"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        # ✅ anchor باید created_at باشد
        "expires_after": {"anchor": "created_at", "seconds": 60},
        "session": {
            "type": "realtime",
            "voice": DEFAULT_VOICE,
            "instructions": (
                "You are Mia, a concise, helpful voice assistant. "
                "Respond in the user's language."
            ),
            # اختیاری:
            # "turn_detection": {"type": "server_vad"},
            # "modalities": ["text", "audio"],
        },
    }

    # (اختیاری) لاگ برای عیب‌یابی
    print(">>> /client_secrets body:", json.dumps(body))

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, headers=headers, json=body)

    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = {"raw": resp.text}
        print("<<< OpenAI error:", json.dumps(detail))
        raise HTTPException(status_code=500, detail=detail)

    data = resp.json()
    print("<<< OK client_secret issued")
    return data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
