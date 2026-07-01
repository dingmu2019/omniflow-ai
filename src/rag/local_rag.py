import os
from loguru import logger
from pipecat.services.openai import OpenAILLMService

def load_knowledge_base() -> str:
    kb_path = "data/knowledge.md"
    if not os.path.exists(kb_path):
        os.makedirs("data", exist_ok=True)
        default_content = """# 公司知识库
- 公司名称: 星辰多模态 AI 科技
- 核心产品: Pipecat 全渠道客服系统、视频去水印工具
- 联系方式: 400-888-8888
- 售后政策: 支持 7 天无理由退款，技术支持 7x24 小时在线。
"""
        with open(kb_path, "w", encoding="utf-8") as f:
            f.write(default_content)
    with open(kb_path, "r", encoding="utf-8") as f:
        return f.read()

async def search_knowledge(args: dict):
    """被 LLM 调用的工具函数"""
    query = args.get("query", "")
    logger.info(f"LLM 正在检索本地知识库，关键词: {query}")
    
    kb_content = load_knowledge_base()
    #    #    #    #    #    #    #    #    # ???   #    #    #    #    #  "result": kb_content}

def register_rag_tool(llm: OpenAILLMService):
    """将本地检索函数注册为 OpenAI 工具"""
    llm.register_function(
        "search_knowledge",
        search_knowledge,
        description="当用户询问公司信息、产品、联系方式或售后政策时，调用此工具搜索本地知识库。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "用户的搜索关键词"}
            },
            "required": ["query"]
        }
    )
