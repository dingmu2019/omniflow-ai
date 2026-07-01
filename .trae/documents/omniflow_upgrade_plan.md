# OmniFlow AI - UI/UX 重构与功能增强计划

## 1. 现状分析
当前项目已实现了基于 `pipecat-ai` 和 WebRTC (Daily) 的隐式连接与音视频通话，并采用了极简的乔布斯设计哲学。
目前存在以下待优化项：
1. **图标使用**：大量使用了 Emoji 作为图标（如 📞、📹 等），在不同操作系统和设备上渲染不一致，缺乏专业感。
2. **语音消息缺失**：目前支持打字和直接进入实时通话，缺乏类似微信的“按住说话 (Push to Talk)”轻量级语音交互方式。
3. **呼叫体验不完整**：目前点击通话会直接进入通话界面，缺少“正在呼叫”的过渡状态；且没有“模拟来电 (Incoming Call)”的接听/挂断演示，无法完整呈现双向呼叫能力。
4. **UI/UX 细节问题**：移动端长按可能触发系统菜单，缺乏 iOS 安全区适配，交互反馈可进一步打磨。

## 2. 拟议更改 (Proposed Changes)

### 2.1 将所有 Emoji 替换为 SVG 图标
**目标文件**：`src/static/index.html`
**修改内容**：
- 移除所有现有的 Emoji（⋯, ⊕, 🖼️, 📞, 📹, 🎤, 🔇, 📷, ⤓）。
- 引入专业、极简的 inline SVG 图标（如使用 Feather Icons 或 Heroicons 风格）。
- 图标颜色通过 CSS 变量 `currentColor` 或 `var(--icon-color)` 适配深浅色主题。

### 2.2 实现“按住说话” (Push to Talk)
**目标文件**：`src/static/index.html`
**修改内容**：
- 在底部输入栏左侧添加一个“语音/键盘”切换 SVG 按钮。
- 切换到语音模式时，隐藏文本输入框 (`.input-box`)，显示一个宽大的“按住 说话”按钮。
- **交互逻辑**：
  - `mousedown` / `touchstart`：调用 `ensureConnection(audio=True, video=False)` 建立/唤醒连接，并执行 `callObject.setLocalAudio(True)` 开启麦克风。显示录音中的 UI 动画提示。
  - `mouseup` / `touchend`：执行 `callObject.setLocalAudio(False)` 关闭麦克风，完成语音发送。
- **防误触处理**：为 PTT 按钮添加 CSS `user-select: none; -webkit-touch-callout: none;` 防止移动端长按弹出菜单。

### 2.3 完善双向呼叫体验 (接听与拨打)
**目标文件**：`src/static/index.html`
**修改内容**：
- **主动呼叫 (拨打)**：
  - 点击“语音/视频通话”时，进入 Call Overlay，状态显示“正在呼叫 OmniFlow...”。
  - 待 Daily `joined-meeting` 且对方（Agent）音频轨道接入后，状态转为“通话中”。
- **模拟来电 (接听)**：
  - 在 Action Panel（➕ 号面板）中新增一个“模拟 AI 来电”测试按钮。
  - 点击后，延迟 2 秒弹出全屏的**来电响铃界面 (Incoming Call UI)**。
  - **来电界面设计**：居中显示 AI 头像和名字，底部提供红色的“拒绝”和绿色的“接听”按钮，附带原生级别的呼吸动效。
  - 点击“接听” -> 执行原有的 `startCall` 逻辑进入通话。
  - 点击“拒绝” -> 关闭来电界面。

### 2.4 UI/UX 全面打磨
**目标文件**：`src/static/index.html`
**修改内容**：
- 增加 `padding-bottom: env(safe-area-inset-bottom);` 以适配 iPhone 底部小黑条。
- 优化 Action Panel 的网格布局和按钮点击态（Ripple / Scale 效果）。
- 确保所有的交互（特别是录音和通话控制）提供明确的视觉反馈（如颜色变化、图标切换）。

## 3. 假设与决策
- **语音消息实现策略**：不采用传统的前端录音生成 mp3/wav 再上传的方案，而是直接复用现有的 WebRTC 连接。长按时解除静音，松开时静音，依靠后端的 VAD（静音检测）和 OpenAI Realtime API 直接处理音频流。这符合本项目的“隐式无感连接”架构。
- **图标选择**：直接在 HTML 中内联 SVG 代码，避免增加外部字体库或图片请求，保持项目零依赖、加载快的特点。

## 4. 验证步骤
1. 打开 `http://localhost:3003`，检查界面所有 Emoji 是否成功替换为 SVG，并且随主题切换颜色。
2. 切换到“按住说话”模式，长按按钮说话，检查是否能听到 AI 的语音回复并在界面上看到字幕/转录。
3. 打开 ⊕ 面板，点击“模拟 AI 来电”，验证 2 秒后是否弹出来电界面，点击接听是否能正常进入通话。
4. 使用 Playwright 自动化脚本验证关键 UI 元素的可见性和点击交互（或手动在浏览器中模拟移动端视口测试）。