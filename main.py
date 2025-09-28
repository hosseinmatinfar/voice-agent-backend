from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

@app.get("/")
def read_root():
    return {"Status": "OK"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected!")
    await websocket.send_text("Connection successful! Ready to receive audio.")
    
    try:
        while True:
            # به جای receive_text از receive_bytes استفاده می‌کنیم
            bytes_data = await websocket.receive_bytes()
            
            # در اینجا، ما باید این داده‌های صوتی رو به OpenAI Whisper بفرستیم
            # اما فعلا برای تست، فقط یک پیام تایید به فلاتر برمی‌گردونیم
            # که نشون بده صدا رو دریافت کردیم.
            
            # اندازه داده دریافتی رو چاپ می‌کنیم تا مطمئن بشیم کار می‌کنه
            print(f"Received audio chunk with size: {len(bytes_data)} bytes")
            
            # یک پیام به فلاتر می‌فرستیم که صدا رو گرفتیم
            # در آینده اینجا جواب واقعی هوش مصنوعی قرار می‌گیره
            await websocket.send_text("Server got your audio chunk! Thinking...")

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"An error occurred: {e}")