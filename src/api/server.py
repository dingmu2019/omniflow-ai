import os
import time
import subprocess
import aiohttp
import glob
import json
import base64
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

# --- 历史记录接口 ---
@app.get("/api/history")
async def get_history():
    """获取所有历史通话的会话列表"""
    os.makedirs("logs", exist_ok=True)
    files = glob.glob("logs/session_*.jsonl")
    sessions = []
    for f in files:
        session_id = os.path.basename(f).replace("session_", "").replace(".jsonl", "")
        # 获取文件最后修改时间
        mtime = os.path.getmtime(f)
        sessions.append({
            "session_id": session_id,
            "timestamp": mtime,
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        })
    # 按时间倒序
    sessions.sort(key=lambda x: x["timestamp"], reverse=True)
    return JSONResponse(sessions)

@app.get("/api/history/{session_id}")
async def get_history_detail(session_id: str):
    """获取单次会话的详细文本记录"""
    file_path = f"logs/session_{session_id}.jsonl"
    if not os.path.exists(file_path):
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    logs = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        return JSONResponse({"session_id": session_id, "logs": logs})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# --- WebRTC 接入层 ---
@app.post("/connect")
async def connect(request: Request):
    if not DAILY_API_KEY or DAILY_API_KEY == "your_daily_api_key_here":
        return JSONResponse({"error": "DAILY_API_KEY 未配置"}, status_code=500)
    
    # 接收前端传来的动态设置
    try:
        body = await request.json()
    except:
        body = {}
        
    system_prompt = body.get("prompt", "你是一个全渠道智能客服。你可以调用 search_knowledge 工具查询公司信息。请用简短、专业的中文回答。")
    voice = body.get("voice", "alloy")
    # 为了避免通过命令行传参时引发特殊字符截断，这里使用 Base64 编码
    prompt_b64 = base64.b64encode(system_prompt.encode('utf-8')).decode('utf-8')
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {DAILY_API_KEY}"}
        async with session.post(f"{DAILY_API_URL}/rooms", headers=headers, json={"properties": {"exp": int(time.time()) + 3600}}) as r:
            room_data = await r.json()
            room_url = room_data.get("url")
        
        async with session.post(f"{DAILY_API_URL}/meeting-tokens", headers=headers, json={"properties": {"room_name": room_data.get("name")}}) as r:
            token_data = await r.json()
            token = token_data.get("token")
    
    # 异步拉起 Pipecat Agent 子进程，并传入 Base64 编码的 Prompt 和音色
    logger.info(f"Spawning Agent for room: {room_url} with voice: {voice}")
    subprocess.Popen([".venv/bin/python", "src/agents/realtime_agent.py", room_url, token, prompt_b64, voice])
    
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
