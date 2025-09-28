from fastapi import FastAPI, WebSocket
import os # برای خواندن متغیرهای محیطی

app = FastAPI()

# این همان مسیر قدیمی ماست که برای تست کردن سلامت سرور خوبه
@app.get("/")
def read_root():
    return {"Hello": "World", "Status": "Ready for WebSocket!"}


# ===> این قسمت جدید و مهم ماست <===
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # منتظر میمانیم تا یک کلاینت (اپ فلاتر ما) وصل شود
    await websocket.accept()
    print("Flutter client connected!")
    
    # OpenAI API Key رو از متغیرهای محیطی که در Render تنظیم کردیم میخونیم
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print("Successfully loaded OpenAI API Key.")
        # یک پیام به کلاینت میفرستیم که کلید با موفقیت پیدا شد
        await websocket.send_text("Connection successful! OpenAI key is configured.")
    else:
        print("WARNING: OPENAI_API_KEY not found!")
        await websocket.send_text("Connection successful, but OpenAI API key is missing on the server.")

    try:
        # در یک حلقه بینهایت منتظر پیام از طرف کلاینت میمانیم
        while True:
            # دریافت پیام از فلاتر (که در آینده صدای ضبط شده خواهد بود)
            data = await websocket.receive_text() # فعلا متن دریافت میکنیم
            print(f"Received message from Flutter: {data}")
            
            # به عنوان جواب، همان پیام را به همراه یک متن اضافه برمیگردانیم (Echo)
            response = f"Server received your message: '{data}'"
            await websocket.send_text(response)
            
    except Exception as e:
        # اگر ارتباط قطع شد یا خطایی رخ داد، در لاگ سرور چاپ میکنیم
        print(f"Client disconnected or error occurred: {e}")
    finally:
        print("Client connection closed.")