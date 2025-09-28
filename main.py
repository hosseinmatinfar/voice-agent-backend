# main.py
import os
import json
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in Render environment variables")

REALTIME_MODEL = os.getenv("REALTIME_MODEL", "gpt-4o-realtime-preview-2024-12-17")
REALTIME_VOICE = os.getenv("REALTIME_VOICE", "alloy")

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
    Create OpenAI Realtime client_secret for WebRTC.
    NOTE: fields must be TOP-LEVEL (no 'session' object).
    """
    url = "https://api.openai.com/v1/realtime/client_secrets"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": REALTIME_MODEL,
        "voice": REALTIME_VOICE,
        "expires_after": 60
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=headers, json=body)

        ct = r.headers.get("content-type", "")
        # موفق
        if r.status_code < 400:
            # اگر JSON بود همون رو پاس بده
            if "application/json" in ct:
                return JSONResponse(r.json(), status_code=r.status_code)
            # در غیر این صورت به شکل متن خام ولی داخل JSON
            return JSONResponse({"raw": r.text}, status_code=r.status_code)

        # خطا از OpenAI
        try:
            err = r.json()
        except Exception:
            err = {"raw": r.text}
        return JSONResponse({"detail": err}, status_code=502)

    except Exception as e:
        return JSONResponse({"detail": {"error": str(e)}}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
