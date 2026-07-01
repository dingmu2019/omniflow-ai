import asyncio
import os
import sys
from loguru import logger
from dotenv import load_dotenv

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.vad.silero import SileroVADAnalyzer

from src.core.log_processor import ConversationLogger
from src.rag.local_rag import register_rag_tool

load_dotenv()

async def main(room_url: str, token: str, prompt_b64: str):
    logger.info("Initializing WebRTC OmniFlow Agent...")
    
    import base64
    try:
        system_prompt = base64.b64decode(prompt_b64).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to decode prompt: {e}")
        system_prompt = "你是一个全渠道智能客服。请用简短、专业的中文回答。"

    transport = DailyTransport(
        room_url=room_url,
        token=token,
        bot_name="OmniFlow",
        params=DailyParams(
            audio_out_enabled=True,
            camera_out_enabled=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        ),
    )

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model="gpt-4o-realtime-preview"
    )
    
    # 挂载 RAG 知识库工具
    register_rag_tool(llm)

    context = OpenAILLMContext(
        [{"role": "system", "content": system_prompt}]
    )
    context_aggregator = llm.create_context_aggregator(context)

    # 实例化全内容留存拦截器 (按 Room ID 隔离日志)
    session_id = room_url.split('/')[-1] if '/' in room_url else "unknown"
    session_logger = ConversationLogger(session_id=session_id)

    # 组装 Pipeline: Transport -> RAG/Context -> LLM -> Logger -> Transport
    pipeline = Pipeline(
        [
            transport.input(),
            context_aggregator.user(),
            llm,
            session_logger, # 旁路记录日志，符合零磁盘占用架构理念
            transport.output(),
        ]
    )

    task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

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
        logger.error("Usage: python realtime_agent.py <room_url> <token> [prompt_b64]")
        sys.exit(1)
    
    room_url = sys.argv[1]
    token = sys.argv[2]
    # 如果没有传入 prompt，给一个默认的 base64
    prompt_b64 = sys.argv[3] if len(sys.argv) > 3 else base64.b64encode("你是一个全渠道智能客服。请用简短、专业的中文回答。".encode('utf-8')).decode('utf-8')
    
    asyncio.run(main(room_url, token, prompt_b64))