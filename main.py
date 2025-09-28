from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI
import os
import io
import wave
import traceback
import asyncio # برای کار با زمانبندی و تاخیر

client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = FastAPI()

def add_wav_header(pcm_data: bytes) -> bytes:
    # ... (این تابع بدون تغییر باقی می‌ماند)
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
    last_audio_time = asyncio.get_event_loop().time()
    processing_task = None

    try:
        while True:
            # ===> منطق جدید تشخیص سکوت <===
            try:
                # منتظر صدای جدید برای حداکثر ۱.۵ ثانیه می‌مانیم
                bytes_data = await asyncio.wait_for(websocket.receive_bytes(), timeout=1.5)
                audio_stream.write(bytes_data)
                last_audio_time = asyncio.get_event_loop().time() # زمان آخرین دریافت صدا رو آپدیت می‌کنیم
                
                # اگر در حال پردازش بودیم، فعلا کاری نمی‌کنیم
                if processing_task and not processing_task.done():
                    continue

            except asyncio.TimeoutError:
                # اگر در ۱.۵ ثانیه گذشته صدایی نیومده باشه و صدایی در بافر داشته باشیم
                if audio_stream.tell() > 20 * 1024: # حداقل ۲۰ کیلوبایت صدا (حدود نیم ثانیه)
                    print("Silence detected, starting AI processing...")
                    
                    # یک تسک جدید برای پردازش صدا ایجاد می‌کنیم تا حلقه اصلی مسدود نشود
                    processing_task = asyncio.create_task(
                        process_audio(websocket, audio_stream)
                    )
                    # استریم رو برای مکالمه بعدی آماده می‌کنیم
                    audio_stream = io.BytesIO()
                continue # به حلقه برمیگردیم تا منتظر صدای بعدی باشیم

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print("An error occurred in main loop:")
        traceback.print_exc()

async def process_audio(websocket: WebSocket, audio_stream: io.BytesIO):
    """این تابع کل منطق پردازش صدا و ارتباط با OpenAI رو انجام میده"""
    try:
        await websocket.send_text("Transcribing...")

        pcm_data = audio_stream.getvalue()
        wav_data = add_wav_header(pcm_data)
        wav_stream = io.BytesIO(wav_data)
        wav_stream.name = "input.wav"
        
        transcript = await client.audio.transcriptions.create(
            model="whisper-1", file=wav_stream
        )
        user_text = transcript.text
        print(f"User said: {user_text}")
        await websocket.send_text(f"You said: {user_text}")

        await websocket.send_text("Thinking...")
        chat_response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful and concise voice assistant named Mia. Respond in the language you are spoken to."},
                {"role": "user", "content": user_text}
            ]
        )
        ai_text_response = chat_response.choices[0].message.content
        print(f"AI response: {ai_text_response}")

        await websocket.send_text("Generating speech...")
        speech_response = await client.audio.speech.create(
            model="tts-1", voice="nova", input=ai_text_response, response_format="mp3"
        )

        print("Sending speech response to Flutter...")
        await websocket.send_bytes(speech_response.content)
        
        print("Processing finished. Waiting for next audio chunk...")
        await websocket.send_text("Listening...")

    except Exception as e:
        print("An error occurred during processing:")
        traceback.print_exc()
        await websocket.send_text(f"An error occurred on the server: {e}")