# OmniFlow 行业顶级体验升级计划 (对标 ChatGPT/微信)

## 1. 摘要
将 OmniFlow AI 升级至行业顶级体验水准，重点解决移动端响应式适配、沉浸式电影级实时字幕、大模型音色切换以及极简零依赖本地知识库的修复与挂载，同时彻底修复底层由于依赖变动和截断产生的致命 Bug。

## 2. 当前状态分析
- **UI 界面**: 目前是纯桌面端分屏设计，在手机端无法正常浏览；缺少沉浸式的字幕反馈机制。
- **配置项**: 设置中仅支持系统提示词 (System Prompt)，缺少业界标配的音色选择。
- **底层 Bug**:
  - `realtime_agent.py` 存在过时/幻觉的 Pipecat 模块导入路径（如 `OpenAILLMContext` 不存在）。
  - `log_processor.py` 存在文件写入截断导致的语法错误（`def __init__` 重复）。
  - `local_rag.py` 存在返回值截断导致的语法错误。

## 3. 具体修改方案

### 3.1 前端 UI 与体验升级 (`src/static/index.html`)
- **响应式布局 (Mobile-First)**: 引入 `@media (max-width: 768px)`，在移动端将左侧视觉区和右侧聊天区改为上下堆叠（Flex-direction: column），并优化按键触控区域大小。
- **悬浮电影字幕**: 在左侧 `.visual-panel` 底部新增绝对定位的半透明字幕层 (`#subtitleOverlay`)。当收到后端的实时流式转录时，以电影字幕风格展示，数秒后自动淡出。
- **音色选择器**: 在“设置”弹窗中新增下拉菜单，支持选择 OpenAI 官方音色（Alloy, Echo, Fable, Onyx, Nova, Shimmer），并将配置与 Prompt 一起存入 LocalStorage。

### 3.2 接入层参数扩充 (`src/api/server.py`)
- 在 `/connect` 接口的 JSON 解析中，提取 `voice` 参数。
- 将 `voice` 参数与 `prompt` 一同通过命令行参数（Base64 编码以防转义）传递给 `realtime_agent.py` 子进程。

### 3.3 核心管道修复与字幕透传 (`src/agents/realtime_agent.py`)
- **修复 Import 路径**: 引入正确的 `pipecat` OpenAI Realtime 依赖库。
- **动态音色设置**: 接收并解析传入的 `voice` 参数，在初始化 `OpenAIRealtimeLLMService` 或配置 Context 时注入。
- **实时字幕广播拦截器**: 新增一个自定义的 `SubtitleProcessor` (继承自 `FrameProcessor`)，专门拦截管道中的 `TranscriptionFrame`（包含用户与 Agent 的实时语音转录），并通过 `transport.send_app_message` 发送至前端，驱动电影字幕更新。

### 3.4 工具链与留存修复 (`src/rag/local_rag.py`, `src/core/log_processor.py`)
- **修复 RAG**: 修正 `local_rag.py` 中的 `search_knowledge` 函数，返回规范的 JSON/字符串结果 `return {"result": kb_content}`，维持零成本零依赖架构。
- **修复 Logger**: 修正 `log_processor.py` 中错乱的类定义，确保文件读写流式记录功能正常运作。

## 4. 假设与前置决策
- **字幕展示策略**: 用户明确选择了“悬浮电影字幕风”，因此实时转录文本只更新在视频/能量球下方，右侧聊天框仅保留最终完整的文本消息（或由用户主动发送的文本）。
- **RAG 策略**: 用户明确选择了“极简本地读取”，无需引入复杂的向量数据库，完全依赖 OpenAI 的 Function Calling 将 Markdown 文本带入上下文。

## 5. 验证步骤
1. 在桌面端与手机端同时访问 `http://localhost:3003`，验证响应式布局是否优雅。
2. 打开设置弹窗，切换音色为 `nova`（女声），发起通话，验证音色是否生效。
3. 在语音通话时，观察视频区下方是否有实时滚动的“电影字幕”。
4. 询问公司地址或退款政策，验证大模型是否成功调用 `search_knowledge` 并基于 `knowledge.md` 给出正确答复。
