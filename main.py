import os, json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# -------- Env --------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in Render environment variables")

REALTIME_MODEL = os.getenv("REALTIME_MODEL", "gpt-4o-realtime-preview-2024-12-17")
DEFAULT_VOICE  = os.getenv("REALTIME_VOICE", "alloy")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

# -------- App --------
app = FastAPI(title="Realtime Token Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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
    ساخت client_secret برای WebRTC Realtime.
    نکته مهم: پارامترها باید top-level باشند (نه داخل 'session').
    """
    url = "https://api.openai.com/v1/realtime/client_secrets"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": REALTIME_MODEL,   # مثال: gpt-4o-realtime-preview-2024-12-17
        "voice": DEFAULT_VOICE,    # مثال: alloy
        "expires_after": 60        # بر حسب ثانیه
        # در صورت نیاز: می‌توانید "instructions" را اضافه کنید.
    }

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
