# main.py
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ------- Env -------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in Render environment variables")

DEFAULT_VOICE = os.getenv("REALTIME_VOICE", "alloy")  # optional
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")   # e.g. "https://your.app,https://other.app"
origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]

# ------- App -------
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
    NOTE:
      - Do NOT send 'model' here. Model is set when posting SDP (?model=...).
      - 'expires_after.anchor' is required by the API.
    """
    url = "https://api.openai.com/v1/realtime/client_secrets"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        # Required by API: anchor + seconds
        "expires_after": {"anchor": "now", "seconds": 60},
        "session": {
            "type": "realtime",
            "voice": DEFAULT_VOICE,
            "instructions": (
                "You are Mia, a concise, helpful voice assistant. "
                "Respond in the user's language."
            ),
            # Optional examples:
            # "turn_detection": {"type": "server_vad"},
            # "modalities": ["text", "audio"],
        },
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, headers=headers, json=body)

    if resp.status_code >= 400:
        # pass OpenAI error transparently
        try:
            detail = resp.json()
        except Exception:
            detail = {"error": resp.text}
        raise HTTPException(status_code=500, detail=detail)

    return resp.json()


# Local run (use Render start command in production):
# uvicorn main:app --host 0.0.0.0 --port $PORT
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
