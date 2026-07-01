#!/bin/bash
source .venv/bin/activate
echo "================================================="
echo "启动 OmniFlow 全流智能客席后台 (Port: 3003)"
echo "测试 Web 端: http://localhost:3003"
echo "Twilio Webhook: http://<你的外网穿透域名>/twilio/voice"
echo "================================================="
uvicorn src.api.server:app --host 0.0.0.0 --port 3003 --reload
