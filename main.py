from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI
import os
import io
import wave
import traceback # برای چاپ خطاهای دقیق‌تر

client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = FastAPI()

def add_wav_header(pcm_data: bytes) -> bytes:
    sample_rate = 16000
    bits_per_sample = 16
    num_channels = 1
    with io.BytesIO() as wav_file:
        with wave.open(wav_file, 'wb') as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(bits_per_sample // 8)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        return wav_file.getvalue()

@app.get("/")
def read_root():
    return {"Status": "OK"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected!")
    
    audio_stream = io.BytesIO()

    try:
        while True:
            bytes_data = await websocket.receive_bytes()
            audio_stream.write(bytes_data)

            # آستانه رو کمی کمتر می‌کنیم تا سریع‌تر جواب بده
            if audio_stream.tell() > 120 * 1024: 
                print("Sufficient audio received, starting AI processing...")
                
                # ===> تغییر ۱: به فلاتر خبر میدیم کار سنگین شروع شد <===
                await websocket.send_text("Transcribing...")

                pcm_data = audio_stream.getvalue()
                wav_data = add_wav_header(pcm_data)
                wav_stream = io.BytesIO(wav_data)
                wav_stream.name = "input.wav"
                
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=wav_stream,
                )
                user_text = transcript.text
                print(f"User said: {user_text}")
                await websocket.send_text(f"You said: {user_text}")

                # ===> تغییر ۲: به فلاتر خبر میدیم داریم فکر می‌کنیم <===
                await websocket.send_text("Thinking...")
                chat_response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a helpful and concise voice assistant named Mia."},
                        {"role": "user", "content": user_text}
                    ]
                )
                ai_text_response = chat_response.choices[0].message.content
                print(f"AI response: {ai_text_response}")

                # ===> تغییر ۳: به فلاتر خبر میدیم داریم صدا میسازیم (مهمترین قسمت) <===
                await websocket.send_text("Generating speech...")
                speech_response = await client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=ai_text_response,
                    response_format="mp3"
                )

                print("Sending speech response to Flutter...")
                await websocket.send_bytes(speech_response.content)

                audio_stream.seek(0)
                audio_stream.truncate()
                
                print("Processing finished. Waiting for next audio chunk...")
                await websocket.send_text("Listening...")

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print("An error occurred:")
        # چاپ کامل خطا برای دیباگ بهتر
        traceback.print_exc()
        await websocket.send_text(f"An error occurred on the server: {e}")