# Realtime Token Service (Render)

## متغیرهای محیطی (Render → Environment)
- `OPENAI_API_KEY`  (اجباری)
- `REALTIME_MODEL`  (اختیاری، پیش‌فرض: gpt-4o-realtime-preview-2024-12-17)
- `REALTIME_VOICE`  (اختیاری، پیش‌فرض: alloy)
- `ALLOWED_ORIGINS` (اختیاری، مثلا: https://your-frontend.com, http://localhost:5173)

## Start Command (Render)
uvicorn main:app --host 0.0.0.0 --port $PORT

## تست
```bash
curl -s https://<your-render-app>.onrender.com/
# => {"status":"ok"}

curl -s -X POST https://<your-render-app>.onrender.com/session | jq
# باید یک آبجکت شامل client_secret برگرداند.
