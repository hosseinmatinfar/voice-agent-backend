# main.py
import os
import json
import base64
import asyncio
from fastapi import FastAPI, WebSocket, HTTPException
import websockets
from openai import AsyncOpenAI

app = FastAPI()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

@app.websocket("/ws/realtime_voice")
async def realtime_voice_websocket(websocket: WebSocket):
    await websocket.accept()
    
    async with websockets.connect(
        OPENAI_REALTIME_URL,
        extra_headers={
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:
        # Load healthcare prompt from file (assumed in assets directory)
        with open("assets/prompts/mia_system_prompt.txt", "r") as f:
            system_prompt = f.read()
        
        await openai_ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": system_prompt,
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {"type": "server_vad"},
                "tools": [
                    {
                        "type": "function",
                        "name": "set_medication_reminder",
                        "description": "Set a medication reminder for a patient",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "medication": {"type": "string"},
                                "time": {"type": "string", "format": "date-time"},
                                "frequency": {"type": "string", "enum": ["daily", "weekly"]}
                            },
                            "required": ["medication", "time"]
                        }
                    }
                ]
            }
        }))
        
        async def forward_to_flutter(data):
            event = json.loads(data)
            if event["type"] == "response.audio.delta":
                audio_chunk = base64.b64decode(event["delta"])
                await websocket.send_json({"audio": base64.b64encode(audio_chunk).decode()})
            elif event["type"] == "input_audio_buffer.speech_started":
                await openai_ws.send(json.dumps({"type": "response.cancel"}))
            elif event["type"] == "response.audio_transcript.done":
                await websocket.send_json({"transcription": event["transcript"]})
            elif event["type"] == "response.content_part.done" and event["part"]["type"] == "text":
                await websocket.send_json({"response_text": event["part"]["text"]})
            elif event["type"] == "response.function_call":
                await websocket.send_json({"name": event["name"], "arguments": event["arguments"]})
            elif event["type"] == "error":
                await websocket.send_json({"error": event["error"]["message"]})
                print(f"OpenAI error: {event['error']}")

        asyncio.create_task(receive_from_openai(openai_ws, forward_to_flutter))
        
        while True:
            try:
                data = await websocket.receive()
                if data.get("type") == "close":
                    break
                elif data.get("bytes"):
                    audio_chunk = data["bytes"]
                    await openai_ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(audio_chunk).decode()
                    }))
                    await openai_ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                    await openai_ws.send(json.dumps({"type": "response.create"}))
                elif data.get("text"):
                    event = json.loads(data["text"])
                    await openai_ws.send(json.dumps(event))
            except Exception as e:
                print(f"WebSocket error: {e}")
                break

async def receive_from_openai(ws, callback):
    async for message in ws:
        await callback(message)

@app.post("/offer")
async def handle_offer(data: dict):
    sdp = data.get("sdp")
    if not sdp:
        raise HTTPException(status_code=400, detail="No SDP provided")
    # Simplified SDP echo for testing; replace with actual WebRTC signaling logic
    return {
        "sdp": sdp,  # Echo back for now; implement real answer SDP
        "ice_servers": [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "turn:turn.example.com", "username": "user", "credential": "pass"}  # Replace with real TURN
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))