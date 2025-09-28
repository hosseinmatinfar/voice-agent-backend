import os, json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in Render environment variables")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]

app = FastAPI(title="Realtime Client Secret Service")

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
async def create_ephemeral_client_secret():
    """
    فقط client_secret می‌گیرد؛ مدل/ویس را اینجا نفرست.
    """
    url = "https://api.openai.com/v1/realtime/client_secrets"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1",
    }
    body = {
        "expires_after": {  # 60 ثانیه کافی است
            "anchor": "created_at",  # یا "now" هم اوکی است
            "seconds": 60
        }
    }

    print(">>> BODY SENT TO OPENAI:", json.dumps(body))
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, headers=headers, json=body)

    # اگر خطا شد، همون خطای OpenAI رو پاس بده بیرون برای دیباگ
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = {"raw": resp.text}
        print("<<< OPENAI ERROR:", json.dumps(detail))
        raise HTTPException(status_code=resp.status_code, detail=detail)

    data = resp.json()
    print("<<< OK client_secret issued")
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
