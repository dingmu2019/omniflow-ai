import asyncio
import os
import sys
from loguru import logger
from dotenv import load_dotenv

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.services.openai.realtime.llm import OpenAIRealtimeLLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.vad.silero import SileroVADAnalyzer

from src.core.log_processor import ConversationLogger
from src.rag.local_rag import register_rag_tool

from pipecat.frames.frames import TextFrame, TranscriptionFrame, Frame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

load_dotenv()

class SubtitleProcessor(FrameProcessor):
    """拦截转录帧并发送给前端展示为电影字幕"""
    def __init__(self, transport: DailyTransport):
        super().__init__()
        self.transport = transport

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        # 只处理发往用户的方向或来自用户的方向
        if isinstance(frame, TranscriptionFrame):
            # 将转录结果发送到前端
            await self.transport.send_app_message({
                "type": "transcription",
                "role": "user" if direction == FrameDirection.UPSTREAM else "agent",
                "text": frame.text
            }, "*")

async def main(room_url: str, token: str, prompt_b64: str, voice: str = "alloy"):
    logger.info(f"Initializing WebRTC OmniFlow Agent with voice: {voice}")
    
    import base64
    try:
        system_prompt = base64.b64decode(prompt_b64).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to decode prompt: {e}")
        system_prompt = "你是一个全渠道智能客服。请用简短、专业的中文回答。"

    # Set up Daily Transport with video enabled
    transport = DailyTransport(
        room_url=room_url,
        token=token,
        bot_name="OmniFlow",
        params=DailyParams(
            audio_out_enabled=True,
            camera_out_enabled=False,
            camera_out_width=1024,
            camera_out_height=768,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        ),
    )

    llm = OpenAIRealtimeLLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model="gpt-4o-realtime-preview"
    )
    # Set the voice
    try:
        # In newer pipecat versions, voice is set via session update or param
        # Here we try to use a method if available, otherwise it defaults.
        if hasattr(llm, 'set_voice'):
            llm.set_voice(voice)
    except Exception as e:
        logger.warning(f"Could not set voice directly: {e}")
    
    # 挂载 RAG 知识库工具
    register_rag_tool(llm)

    context = LLMContext(
        [{"role": "system", "content": system_prompt}]
    )
    context_aggregator = llm.create_context_aggregator(context)

    # 实例化全内容留存拦截器 (按 Room ID 隔离日志)
    session_id = room_url.split('/')[-1] if '/' in room_url else "unknown"
    session_logger = ConversationLogger(session_id=session_id)
    
    # 字幕处理器
    subtitle_processor = SubtitleProcessor(transport)

    # 组装 Pipeline: Transport -> Subtitle -> RAG/Context -> LLM -> Logger -> Transport
    pipeline = Pipeline(
        [
            transport.input(),
            subtitle_processor,
            context_aggregator.user(),
            llm,
            session_logger, # 旁路记录日志，符合零磁盘占用架构理念
            transport.output(),
        ]
    )

    task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

    @transport.event_handler("on_app_message")
    async def on_app_message(transport, message, sender_id):
        logger.info(f"Received App Message from {sender_id}: {message}")
        if isinstance(message, dict) and "type" in message:
            msg_type = message["type"]
            if msg_type == "text":
                text_content = message.get("content", "")
                # 中断当前的音频播放，插入文本帧
                await task.queue_frame(TextFrame(text_content))
            elif msg_type == "image":
                # 收到前端发来的图片（通过 Data Channel）
                logger.info("Received an image via Data Channel")
                # 可以将其加入到 Vision Context 中，或封装为特定的 Frame 交给支持 Vision 的大模型
                pass

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        logger.info(f"User {participant['id']} joined. Starting conversation...")
        await transport.capture_participant_transcription(participant["id"])
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    runner = PipelineRunner()
    logger.info("Pipeline built, running...")
    await runner.run(task)

if __name__ == "__main__":
    import base64
    if len(sys.argv) < 3:
        logger.error("Usage: python realtime_agent.py <room_url> <token> [prompt_b64] [voice]")
        sys.exit(1)
    
    room_url = sys.argv[1]
    token = sys.argv[2]
    prompt_b64 = sys.argv[3] if len(sys.argv) > 3 else base64.b64encode("你是一个全渠道智能客服。请用简短、专业的中文回答。".encode('utf-8')).decode('utf-8')
    voice = sys.argv[4] if len(sys.argv) > 4 else "alloy"
    
    asyncio.run(main(room_url, token, prompt_b64, voice))
