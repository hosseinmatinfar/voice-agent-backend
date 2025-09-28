from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI # از نسخه Async استفاده میکنیم که سرعت بالاتری داره
import os
import io

# --- کلاینت OpenAI ---
# کلید API رو که در Render ذخیره کردیم، اینجا میخونه
# مطمئن شو که اسم متغیر محیطی در Render دقیقا OPENAI_API_KEY باشه
client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = FastAPI()

@app.get("/")
def read_root():
    return {"Status": "OK", "Message": "AI Backend is running."}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected!")
    
    # یک استریم (جریان) در حافظه برای ذخیره تکه‌های صوتی ایجاد می‌کنیم
    audio_stream = io.BytesIO()

    try:
        while True:
            # داده‌های باینری (صدا) رو از فلاتر دریافت می‌کنیم
            bytes_data = await websocket.receive_bytes()
            
            # هر تکه صدا رو به انتهای استریم اضافه می‌کنیم
            audio_stream.write(bytes_data)

            # نکته: در یک پروژه واقعی، باید یک منطق برای تشخیص پایان صحبت کاربر
            # (Voice Activity Detection) اضافه کنیم.
            # فعلا برای سادگی، فرض می‌کنیم بعد از دریافت یک حجم مشخصی از داده،
            # صحبت کاربر تمام شده و باید پردازش رو شروع کنیم.
            # برای مثال، بعد از دریافت حدود 500 کیلوبایت داده (چند ثانیه صحبت).
            if audio_stream.tell() > 150 * 1024: # حدودا معادل ۴-۵ ثانیه صحبت
                print("Sufficient audio received, starting AI processing...")
                
                # به فلاتر میگیم که در حال پردازش هستیم
                await websocket.send_text("Processing your request...")

                # --- 1. تبدیل صدا به متن (Speech-to-Text با Whisper) ---
                audio_stream.seek(0) # استریم رو به اول برمیگردونیم تا خونده بشه
                
                # Whisper برای اینکه فرمت فایل رو تشخیص بده، نیاز به یک اسم فایل داره
                # ما یک اسم ساختگی بهش میدیم
                audio_stream.name = "input.wav"
                
                print("Transcribing audio...")
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_stream,
                )
                user_text = transcript.text
                print(f"User said: {user_text}")

                # به فلاتر میگیم که حرفش رو فهمیدیم
                await websocket.send_text(f"You said: {user_text}")


                # --- 2. گرفتن جواب از مدل زبان (GPT-4o) ---
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

                
                # --- 3. تبدیل متن جواب به صدا (Text-to-Speech) ---
                print("Generating speech response...")
                speech_response = await client.audio.speech.create(
                    model="tts-1",
                    voice="nova", # میتونی صداهای دیگه مثل alloy, echo, fable, onyx, shimmer رو امتحان کنی
                    input=ai_text_response,
                    response_format="mp3" # فرمت خروجی
                )

                # صدای تولید شده رو به صورت باینری به فلاتر میفرستیم
                print("Sending speech response to Flutter...")
                await websocket.send_bytes(speech_response.content)

                # استریم صدا رو برای مکالمه بعدی خالی می‌کنیم
                audio_stream.seek(0)
                audio_stream.truncate()
                
                print("Processing finished. Waiting for next audio chunk...")
                await websocket.send_text("Listening...")


    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"An error occurred: {e}")
        # اگر خطایی رخ داد، به فلاتر هم اطلاع میدیم
        await websocket.send_text(f"An error occurred on the server: {e}")