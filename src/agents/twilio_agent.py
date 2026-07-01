import os
from fastapi import WebSocket
from loguru import logger
from dotenv import load_dotenv

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.network.fastapi_websocket import FastAPIWebsocfrom pipecat.transports.network.fastapi_websocket import FastAPIWebsocfrom pipecat.transports.network.fastapi_websocket import FastAPIWebsocfrom pipecat.transports.network.fastapi_websocket import FastAPIWebsocfrom pipecat.transports.network.fastapi_websocket import FastAPIWebsocfrom pipecat.transports.network.fastapi_websocket import FastAPIWebsocfrom pipecat.transports.network.fastapi_websocket import FastAPIWebsocfrom pipecat.transports.network.fastapi_websocket impoockfrom pipecat.transports.network.fastapi_weue,
            add_wav_header=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        )
    )

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model="gpt-4o-realtime-preview"
    )
    
    register_rag_tool(llm)

    context = OpenAILLMContext(
        [{"role": "system", "content": "你是一个电话客服。回答要非常简短，适合语音播报。你可以查询知识库。"}]
    )
    context_aggregator = llm.create_context_aggregator(context)
    session_logger = ConversationLogger(session_id="twilio_call")

    pipeline = Pipeline(
        [
            transport.input(),
            context_aggregator.user(),
            llm,
            session_logger,
            transport.output(),
        ]
    )

    task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))
    runner = PipelineRunner()
    
    logger.info("Twilio Pipeline running...")
    await runner.run(task)
