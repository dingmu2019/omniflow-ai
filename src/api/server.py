import os
import time
import subprocess
import aiohttp
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from loguru import logger

load_dotenv()
app = FastAPI(title="OmniFlow Server")

DAILY_API_KEY = os.getenv("DAILY_API_KEY")
DAILY_API_URL = "https://api.daily.co/v1"

app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/")
async def index():
    with open("src/static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# --- WebRTC 接入层 ---
@app.post("/connect")
async def connect():
    if not DAILY_API_KEY or DAILY_API_KEY == "your_daily_api_key_here":
        return JSONResponse({"error": "DAILY_API_KEY 未配置"}, status_code=500)
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {DAILY_API_KEY}"}
        async with session.post(f"{DAILY_API_URL}/rooms", headers=headers, json={"properties": {"exp": int(time.time()) + 3600}}) as r:
            room_data = await r.json()
            room_url = room_data.get("url")
        
        async with session.post(f"{DAILY_API_URL}/meeting-tokens", headers=headers, json={"properties": {"room_name": room_data.get("name")}}) as r:
            token_data = await r.json()
            token = token_data.get("token")
    
    # 异步拉起 Pipecat Agent 子进程
    logger.info(f"Spawning Agent for room: {room_url}")
    subprocess.Popen([".venv/bin/python", "src/agents/realtime_agent.py", room_url, token])
    
    return JSONResponse({"room_url": room_url, "token": token})

# --- PSTN 电话接入层 (Twilio) ---
@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    """Twilio Webhook: 接收电话呼入并重定向到 WebSocket"""
    host = request.headers.get("host")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Connect>
            <Stream url="wss://{host}/twilio/ws" />
        </Connect>
    </Response>"""
    return Response(content=twiml, media_type="application/xml")

@app.websocket("/twilio/ws")
async def twilio_ws(websocket: WebSocket):
    """处理 Twilio 的音频流 WebSocket"""
    await websocket.accept()
    logger.info("Twilio PSTN call connected. Starting Pipeline...")
    from src.agents.twilio_agent import run_twilio_pipeline
    await run_twilio_pipeline(websocket)
