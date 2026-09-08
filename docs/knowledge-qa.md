# 领域知识问答与 DeepSeek

左侧知识模块的核心交互是用户提问与追问。回答区与原文依据分开，点击引用可定位对应来源。
当前公开版不保存会话到服务器；可以自愿开启本地浏览器会话记忆，新对话隔离当前上下文。最近 8 条有效历史消息用于解析追问，
显式追问通过回溯最近明确主题辅助检索，独立问题切换主题。这是规则上下文策略，还不是模型查询改写。

## 两种运行方式

- GitHub Pages：浏览器检索自编示例资料，显示原文摘录，明确标注没有调用大模型。
- 本机 DeepSeek：浏览器请求本地 8090 端口，Python 检索后加载专用 Skill，再请求 DeepSeek。

先按 README 创建 Python 环境、安装依赖。在 PowerShell 的仓库目录运行：

```powershell
& .\tools\start_knowledge_api.ps1
```

已有 API Key 时直接使用，否则脚本会隐藏输入 API Key。默认模型为 `deepseek-v4-flash`，支持预先设置
`DS_API_KEY` 与 `DS_MODEL`，也兼容 `DEEPSEEK_API_KEY` 与 `DEEPSEEK_MODEL`。两组同时配置时优先使用 DS 变量。脚本输入的环境变量仅供当前进程和子进程使用，不写入文件。
`.env.example` 只列出变量名，程序不会自动加载 `.env`。
另一个终端在 frontend 下执行 `npm run dev`，打开本地知识问答页，勾选“使用本地 DeepSeek”再提问。
脚本可用 `-Python` 指定已有 Python 解释器，不必重复安装环境。

## Skill 的实际作用

- `skills/vpn-evidence-workbench/SKILL.md`：开发设计约束，明确该模块以知识问答为主。
- `backend/traffic_agent/skills/vpn-knowledge-qa/SKILL.md`：每次知识回答调用时实际读取，规定中文解释、来源引用、知识不足处理及 JSON 格式。
- `traffic-evidence-review`：单独用于候选流的分析报告，不替代用户知识问答。

代码执行输出结构校验、来源 ID 校验和异常处理。检索资料与历史消息按不可信数据传入，
不能覆盖系统指令。无检索结果时直接提示资料不足，不发出付费请求。

## 验证边界

单元测试以 HTTP Mock 验证缺少配置、JSON 空内容与截断、超时、未知引用，以及提示词和 token 统计。
2026-09-07 使用已配置的环境变量完成一次真实 DeepSeek smoke 验证：返回 3 段回答、3 个来源，
耗时约 15.6 秒，共 3037 tokens。此记录是单例功能验证，不作为效果基准。引用存在性校验不等于语义支持度验证。
当前 3 篇自编文档只是工程样例，回答覆盖面有限，之后需要扩展公开协议资料和评测集。

随后通过真实浏览器验证了本地前端、Python API、DeepSeek 与引用展示的完整链路：
另一条“开放集拒识是什么意思？”问题耗时约 4.3 秒、1136 tokens。
以下截图已更新为后续流式请求结果，并非预设模型回答。

![真实 DeepSeek 知识问答](assets/knowledge-qa-deepseek.png)

DeepSeek 的 JSON 输出使用 `response_format: {type: json_object}`，并在提示词中规定 JSON 格式；
实现参考 [官方 JSON Output 文档](https://api-docs.deepseek.com/guides/json_mode/)。

## 流式响应与会话记忆

浏览器使用 POST fetch 读取 `/api/knowledge/answer/stream`。后端通过异步 HTTP 客户端实际开启
DeepSeek `stream: true`，不是一次性生成后再做打字动画。协议参考
[官方 Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)。

事件顺序为 `status → sources → draft* → done`，失败使用 `error`。JSON 增量尚不完整时，
只解析可读取的段落文字，标注为未校验草稿；最后要求完整 JSON、正常结束与来源 ID 校验，才展示正式答案。
不转发原始 JSON、隐藏推理或密钥。未知引用、截断、上游故障会撤回草稿，且不进入后续上下文。

浏览器停止按钮使用 AbortController；后端取消向上传播并关闭 HTTP 流。后端 65 秒总超时、
输出字符上限，客户端也设超时与 SSE 帧大小上限。前端支持 UTF-8 跨字节分块、CRLF 与异常 EOF。
响应附带 `X-Accel-Buffering: no`。若后续通过 Nginx 代理，还需验证实际代理缓冲及读取超时配置。
当前为单次 POST 流，不支持断点续传，也不自动重试付费请求。

![真实生成中的草稿与停止按钮](assets/knowledge-qa-streaming.png)

记忆采用两层简单实现：

- 会话记录：用户主动开启后写入本机 localStorage，最多 5 个会话、每个 20 个有效轮次；7 天过期，在加载时清理。支持刷新恢复、切换、新会话隔离和全部删除。不开启则刷新不保留。
- 模型上下文：只选当前会话成功回答及其问题，最多 8 条消息，总计 8000 字符；后端再次限长。历史不是检索证据，不授予系统指令权限。

字符预算不等于 tokenizer 精确 token 预算；没有摘要压缩、跨会话语义记忆或服务端用户隔离。
本地记录不是加密保险箱，共用浏览器不要保存敏感问题；浏览器存储禁用或容量不足会提示且不阻断当前问答。

![移动端恢复后的资料摘录会话](assets/knowledge-qa-memory-mobile.png)

2026-09-07 单次真实流式验证：首段可见草稿 2782ms、最终完成 6828ms、1319 tokens。
首段草稿计时包含检索和上游调用，不是纯模型 TTFT；单例数据不用于宣称平均性能或准确率。
Playwright 验证真实草稿与最终引用、刷新恢复、新会话隔离、切换、删除和 390px 布局；
另以浏览器模拟流验证停止与草稿撤回，以 Python Mock 流验证取消关闭上游。共 29 项 Python 与 14 项 Node 测试通过。

复现入口：`tools/check_live_knowledge_ui.js` 会触发一次付费请求；`tools/check_stream_ui.js`
是无付费的停止交互测试。`tools/check_memory_ui.js` 可在已有成功回答的页面继续验证，无需再次请求模型。

下一步优先做可标注的追问与证据支持度评测，再基于失败案例增加查询改写、历史摘要或服务端记忆，
而不是先引入向量记忆数据库来增加架构复杂度。

## 连续追问的主题保留

2026-09-08 修正了旧的“短问题拼接上一句”策略：第二次问“举个例子”时，上一句可能只有“为什么呢”，
此时原始主题已经丢失；短的新主题如“UDP”又可能误拼上旧话题。

现在前后端共用 `shared/followup-policy.json`，仅对明确的通用追问回溯最近 8 条消息中的用户主题，
跳过“为什么”“举个例子”等无主题消息，不使用助手回答作为主题锚点。独立问题不拼历史，
找不到主题时返回 `NEEDS_CONTEXT` 请求补充且不调用模型。页面可展开“追问理解与检索词”查看策略结果。

共用 `shared/followup-cases.json` 的 12 个手写策略用例覆盖连续追问、切换主题、标点、仅助手历史和无上下文，
另测历史窗口隔离与实际检索结果。这是开发回归样例，不是独立质量评测集，不报告准确率提升。
当前共 31 项 Python、15 项 Node 测试。规则只覆盖列明的追问表达，不宣称理解任意指代或隐含话题切换。
