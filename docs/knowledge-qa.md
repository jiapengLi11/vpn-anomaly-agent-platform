# 领域知识问答与 DeepSeek

左侧知识模块的核心交互是用户提问与追问。回答区与原文依据分开，点击引用可定位对应来源。
当前公开版不保存会话到服务器；新对话清空当前页面记录。最近 8 条历史消息用于解析追问，
短问题通过拼接上一条用户问题辅助检索。这是简单上下文策略，还不是模型查询改写。

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
以下截图来自这次真实请求，并非预设模型回答。

![真实 DeepSeek 知识问答](assets/knowledge-qa-deepseek.png)

DeepSeek 的 JSON 输出使用 `response_format: {type: json_object}`，并在提示词中规定 JSON 格式；
实现参考 [官方 JSON Output 文档](https://api-docs.deepseek.com/guides/json_mode/)。
