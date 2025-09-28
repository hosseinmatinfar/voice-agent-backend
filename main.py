from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI
import os
import io
import wave # <--- کتابخانه استاندارد پایتون برای کار با فایل‌های WAV

# --- کلاینت OpenAI ---
client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = FastAPI()


# === تابع کمکی برای اضافه کردن هدر WAV ===
def add_wav_header(pcm_data: bytes) -> bytes:
    """اطلاعات هدر یک فایل WAV را به داده‌های خام PCM اضافه می‌کند."""
    
    # مشخصات صدای ضبط شده در فلاتر
    sample_rate = 16000  # 16kHz
    bits_per_sample = 16 # 16-bit
    num_channels = 1     # Mono

    # ایجاد یک فایل WAV در حافظه
    with io.BytesIO() as wav_file:
        with wave.open(wav_file, 'wb') as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(bits_per_sample // 8)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        
        # برگرداندن کل محتوای فایل (هدر + داده‌ها)
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

            if audio_stream.tell() > 150 * 1024:
                print("Sufficient audio received, starting AI processing...")
                await websocket.send_text("Processing your request...")

                # --- 1. تبدیل صدا به متن (با هدر WAV) ---
                pcm_data = audio_stream.getvalue()
                
                # ===> تغییر کلیدی اینجاست <===
                wav_data = add_wav_header(pcm_data)
                
                # فایل WAV ساخته شده در حافظه رو به OpenAI میفرستیم
                wav_stream = io.BytesIO(wav_data)
                wav_stream.name = "input.wav" # اسم فایل هنوز لازمه
                
                print("Transcribing audio...")
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=wav_stream,
                )
                user_text = transcript.text
                print(f"User said: {user_text}")
                await websocket.send_text(f"You said: {user_text}")


                # --- 2. گرفتن جواب از GPT-4o ---
                print("Getting response from GPT-4o...")
                chat_response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a helpful and concise voice assistant named Mia."},
                        {"role": "user", "content": user_text}
                    ]
                )
                ai_text_response = chat_response.choices[0].message.content
                print(f"AI response: {ai_text_response}")

                
                # --- 3. تبدیل متن جواب به صدا (TTS) ---
                print("Generating speech response...")
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
        print(f"An error occurred: {e}")
        await websocket.send_text(f"An error occurred on the server: {e}")