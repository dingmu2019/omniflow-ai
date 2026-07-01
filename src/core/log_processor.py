import os
import json
from datetime import datetime
from loguru import logger

from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.frames.frames import TranscriptionFrame, TextFrame, Frame

class ConversationLogger(FrameProcessor):
    """全内容留存：旁路拦截器，记录用户转录与 LLM 回复"""
    def __init__(self, session_id: str = "default"):
        super().__init__()
        self.session_id = session_id
        os.makedirs("logs", exist_ok=True)
        self.log_file = f"logs/session_{session_id}.jsonl"

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, TranscriptionFrame):
            self._write_log("User", frame.text)
        elif isinstance(frame, TextFrame):
            self._write_log("Agent", frame.text)

    def _write_log(self, role: str, text: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "text": text
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write log: {e}")
