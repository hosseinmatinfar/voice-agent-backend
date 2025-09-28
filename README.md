# Mia Realtime Token Service (Render)

## Env Vars (Render)
- OPENAI_API_KEY = sk-...                # کلید OpenAI
- REALTIME_VOICE = alloy                 # اختیاری

## Start Command (Render)
uvicorn main:app --host 0.0.0.0 --port $PORT

## Test
curl -X POST https://voice-agent-backend-tn1g.onrender.com

# باید JSON برگرداند که شامل client_secret.value باشد.

