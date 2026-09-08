# Tool Router 与分层评测

## Tool Router 为什么放在 Agent 前面

平台的工具不是越多越好，关键是模型不能绕过安全准入自由调用。当前 Tool Router 位于
`security_admission` 之后、任何检索或模型请求之前。它只读取已脱敏的候选摘要，并产生一个可审计执行计划。

当前注册表只有两个能力：

| 工具 | 类型 | 依赖 | 当前实现 |
| --- | --- | --- | --- |
| `knowledge.search` | 本地检索 | 无 | 从候选证据代码构造 BM25 查询，最多调用一次 |
| `analyst.review` | 外部模型 | `knowledge.search` | 根据准入证据与检索片段生成结构化研判，最多调用一次 |

默认计划按 `knowledge.search → analyst.review` 执行。显式请求也必须使用注册表中的精确名称并满足依赖。
`shell.exec` 等未知名字、缺少证据、只请求模型却跳过检索都会得到拒绝计划；工作流直接进入 `finalize`，
不调用下游函数，`securityVerdict` 仍为 `UNKNOWN`。路由状态、选中数量、拒绝数量和版本写入 Agent trace。

这版选择确定性策略，是因为工具只有两个，安全边界比自然语言意图覆盖更重要。未来可以让小模型提出候选工具，
但候选仍需经过同一个注册表、参数 schema、依赖和权限策略，不能把模型输出直接当执行计划。
`GET /api/tools` 只暴露注册元数据，不暴露密钥或函数对象。

## MCP Bridge

`POST /api/mcp` 提供应用内 JSON-RPC 2.0 适配层：`tools/list` 返回同一份注册表的名称、描述、输入 schema、版本、依赖和最大调用次数；`tools/call` 只允许注册工具，并在执行前校验必填字段、类型、长度和数量上限。

`knowledge.search` 调用本地检索；`analyst.review` 委托给现有 `AgentWorkflow`，因此仍会经过安全准入、Tool Router、知识检索和 Claim Gate。分析工具还复用 requestId 计费预授权，失败会释放额度。这个实现是本地 Bridge，不冒充已经完成的独立 MCP Server；后续可以在不改工具规则的前提下增加 stdio 或 streamable HTTP 传输。

## 分层评测设计

评测按故障定位能力分层，不把所有问题压成一个“准确率”：

| 层级 | 关注点 | 当前证据 | 下一步 |
| --- | --- | --- | --- |
| L0 合同与安全 | schema、引用 ID、工具白名单、依赖、脱敏 | 单元测试与恶意工具名用例 | 文档注入、参数污染、自由文本 DLP |
| L1 检索与上下文 | Hit@K、MRR、域外空结果、追问解析 | 版本化自编开发集与 CI 门槛 | 独立标注集、向量/RRF 对比 |
| L2 回答质量 | 事实支持度、完整性、不确定性、拒答 | 7 个自编案例、自动合同、运行冻结与人工复核表 | 独立双人标注；LLM Judge 仅辅助并校准一致性 |
| L3 Agent 链路 | 路由、短路、降级、Claim Gate、MCP Bridge、trace | 合成端到端回归 | 正式 MCP 传输、人审中断与恢复 |
| L4 运行质量 | 首段延迟、完成延迟、token、取消、错误率 | 单次流式 smoke 与取消测试 | 多次分位数、费用口径、故障注入 |
| L5 业务效果 | 候选研判正确性、漏报/误报、人工收益 | 未建立 | 合法来源样本、盲测和人工复核反馈 |

### 已实现的 L1 基线

`evaluation/knowledge-retrieval-v1.json` 包含 12 个域内问题、5 个域外问题和 4 个多轮场景。
`tools/evaluate_knowledge.py` 计算 Hit@1、Hit@3、MRR、域外拒答、追问解析和引用合同，输出机器可读 JSON
与[可读报告](knowledge-evaluation.md)。CI 每次重建报告、执行门槛并用 `git diff --exit-code` 检查结果是否漂移。

当前结果来自与语料同源的手写开发集，因此只证明已知场景没有回归。它不能支持“线上准确率”、
“RAG 准确率”或“幻觉率下降”等简历结论。扩大语料后应冻结独立测试集，再比较 BM25、向量与融合方案。

### 已实现的 L2 回答评测

`evaluation/answer-quality-v1.json` 为问题标注关键概念、必需引用章节和不可输出结论，并包含域外拒答案例。
运行器冻结模型输出，评测器生成机器报告和人工复核队列。人工评价拆成：

- `faithfulness`：回答中的事实是否能被引用片段支持；
- `coverage`：关键事实是否遗漏；
- `abstention`：资料不足时是否拒绝补造；
- `boundary`：是否把知识背景误写成当前流量事实；
- `actionability`：后续检查建议是否具体且不越权。

模型裁判可以降低初筛成本，但必须用人工样本校准，记录提示词、裁判模型和一致性；不能把同一个模型自评当作最终效果。

当前实际运行的是确定性 `demo-extractive` 基线：5 个域内问题返回来源摘录，2 个域外问题拒答，自动合同通过率
为 100%，token 为 0。这个结果只证明开发集上的检索、引用、拒答和评测流水线没有回归，不代表 LLM 回答质量。
[完整运行报告](answer-quality-evaluation.md)保留 `EXTRACTIVE` 模式与人工复核 `PENDING` 标记。
