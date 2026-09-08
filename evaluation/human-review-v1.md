# Human Review Queue

Status: **PENDING**. This file intentionally contains no invented human scores. Review each answer against the supplied source text; do not reward unsupported outside knowledge.

Scale: 0 = fails, 1 = partial, 2 = supported. A second reviewer is required before reporting agreement or a human quality score.

## A01: 开放集拒识是什么意思？为什么 unknown 不能直接看作恶意流量？

**Expected behavior:** ANSWER
**Observed status:** EXTRACTIVE

**Answer**

序列编码分类器输出类别预测。开放集拒识 unknown 用于表达输入超出已知类别或模型信心不足；它不等于发现恶意流量。分类结果应携带执行后端和模型版本，并与确定性特征证据共同进入候选筛选。

调查候选 candidate 表示需要复核。长会话 LONG_SESSION 与双向均衡 BALANCED_EXCHANGE 可以作为调查线索，但不能单独证明 VPN、攻击或恶意通信。观察到的事实、模型预测与知识参考必须分别记录。

**Retrieved sources**

- `KB-1f3b587c6c36b2a0` 序列分类与开放集拒识: 序列编码分类器输出类别预测。开放集拒识 unknown 用于表达输入超出已知类别或模型信心不足；它不等于发现恶意流量。分类结果应携带执行后端和模型版本，并与确定性特征证据共同进入候选筛选。
- `KB-c9a7f7bac49a9c03` 调查候选不是恶意结论: 调查候选 candidate 表示需要复核。长会话 LONG_SESSION 与双向均衡 BALANCED_EXCHANGE 可以作为调查线索，但不能单独证明 VPN、攻击或恶意通信。观察到的事实、模型预测与知识参考必须分别记录。
- `KB-1261a365d7c6dba7` UDP 会话与双向流量: UDP 会话特征应结合包数、字节数、持续时间和双向比例解释。BALANCED_EXCHANGE 表示双向交换信号；业务同步、实时通信也可能出现类似观测。请关联资产角色与业务时段，不按单个端口直接判定协议。
- `KB-7de8fb605796915e` 引用与人工复核: 调查建议 INVESTIGATE 应引用当前会话的证据 ID，并核对证据强度和会话归属。知识文档只提供解释背景，不证明当前会话具备文档描述的行为。证据不足时保留 UNKNOWN，并列出需要人工核实的资产、业务用途和历史连接。

**Human rubric (0-2 each; leave evidence in notes)**

- [ ] Faithfulness: __ / 2
- [ ] Coverage: __ / 2
- [ ] Boundary and uncertainty: __ / 2
- [ ] Actionability: __ / 2
- [ ] Abstention correctness: __ / 2 or N/A
- Reviewer: __
- Notes: __

## A02: 解释 UDP 会话和双向均衡时要看哪些特征？为什么不能只按端口判断？

**Expected behavior:** ANSWER
**Observed status:** EXTRACTIVE

**Answer**

UDP 会话特征应结合包数、字节数、持续时间和双向比例解释。BALANCED_EXCHANGE 表示双向交换信号；业务同步、实时通信也可能出现类似观测。请关联资产角色与业务时段，不按单个端口直接判定协议。

调查候选 candidate 表示需要复核。长会话 LONG_SESSION 与双向均衡 BALANCED_EXCHANGE 可以作为调查线索，但不能单独证明 VPN、攻击或恶意通信。观察到的事实、模型预测与知识参考必须分别记录。

**Retrieved sources**

- `KB-1261a365d7c6dba7` UDP 会话与双向流量: UDP 会话特征应结合包数、字节数、持续时间和双向比例解释。BALANCED_EXCHANGE 表示双向交换信号；业务同步、实时通信也可能出现类似观测。请关联资产角色与业务时段，不按单个端口直接判定协议。
- `KB-c9a7f7bac49a9c03` 调查候选不是恶意结论: 调查候选 candidate 表示需要复核。长会话 LONG_SESSION 与双向均衡 BALANCED_EXCHANGE 可以作为调查线索，但不能单独证明 VPN、攻击或恶意通信。观察到的事实、模型预测与知识参考必须分别记录。
- `KB-7de8fb605796915e` 引用与人工复核: 调查建议 INVESTIGATE 应引用当前会话的证据 ID，并核对证据强度和会话归属。知识文档只提供解释背景，不证明当前会话具备文档描述的行为。证据不足时保留 UNKNOWN，并列出需要人工核实的资产、业务用途和历史连接。
- `KB-1f3b587c6c36b2a0` 序列分类与开放集拒识: 序列编码分类器输出类别预测。开放集拒识 unknown 用于表达输入超出已知类别或模型信心不足；它不等于发现恶意流量。分类结果应携带执行后端和模型版本，并与确定性特征证据共同进入候选筛选。

**Human rubric (0-2 each; leave evidence in notes)**

- [ ] Faithfulness: __ / 2
- [ ] Coverage: __ / 2
- [ ] Boundary and uncertainty: __ / 2
- [ ] Actionability: __ / 2
- [ ] Abstention correctness: __ / 2 or N/A
- Reviewer: __
- Notes: __

## A03: LONG_SESSION 和周期性连接应该怎样复核？

**Expected behavior:** ANSWER
**Observed status:** EXTRACTIVE

**Answer**

LONG_SESSION 长会话只说明持续时间触及配置阈值。周期性连接还应检查时间间隔、抖动和重复次数。阈值属于可调整策略，报告应保留观测值、阈值、规则版本与证据 ID，便于复查触发原因。

调查候选 candidate 表示需要复核。长会话 LONG_SESSION 与双向均衡 BALANCED_EXCHANGE 可以作为调查线索，但不能单独证明 VPN、攻击或恶意通信。观察到的事实、模型预测与知识参考必须分别记录。

**Retrieved sources**

- `KB-28da04190972691e` 长会话与周期性: LONG_SESSION 长会话只说明持续时间触及配置阈值。周期性连接还应检查时间间隔、抖动和重复次数。阈值属于可调整策略，报告应保留观测值、阈值、规则版本与证据 ID，便于复查触发原因。
- `KB-c9a7f7bac49a9c03` 调查候选不是恶意结论: 调查候选 candidate 表示需要复核。长会话 LONG_SESSION 与双向均衡 BALANCED_EXCHANGE 可以作为调查线索，但不能单独证明 VPN、攻击或恶意通信。观察到的事实、模型预测与知识参考必须分别记录。
- `KB-7de8fb605796915e` 引用与人工复核: 调查建议 INVESTIGATE 应引用当前会话的证据 ID，并核对证据强度和会话归属。知识文档只提供解释背景，不证明当前会话具备文档描述的行为。证据不足时保留 UNKNOWN，并列出需要人工核实的资产、业务用途和历史连接。

**Human rubric (0-2 each; leave evidence in notes)**

- [ ] Faithfulness: __ / 2
- [ ] Coverage: __ / 2
- [ ] Boundary and uncertainty: __ / 2
- [ ] Actionability: __ / 2
- [ ] Abstention correctness: __ / 2 or N/A
- Reviewer: __
- Notes: __

## A04: 为什么调查候选不能直接当成恶意结论？

**Expected behavior:** ANSWER
**Observed status:** EXTRACTIVE

**Answer**

调查候选 candidate 表示需要复核。长会话 LONG_SESSION 与双向均衡 BALANCED_EXCHANGE 可以作为调查线索，但不能单独证明 VPN、攻击或恶意通信。观察到的事实、模型预测与知识参考必须分别记录。

序列编码分类器输出类别预测。开放集拒识 unknown 用于表达输入超出已知类别或模型信心不足；它不等于发现恶意流量。分类结果应携带执行后端和模型版本，并与确定性特征证据共同进入候选筛选。

**Retrieved sources**

- `KB-c9a7f7bac49a9c03` 调查候选不是恶意结论: 调查候选 candidate 表示需要复核。长会话 LONG_SESSION 与双向均衡 BALANCED_EXCHANGE 可以作为调查线索，但不能单独证明 VPN、攻击或恶意通信。观察到的事实、模型预测与知识参考必须分别记录。
- `KB-1f3b587c6c36b2a0` 序列分类与开放集拒识: 序列编码分类器输出类别预测。开放集拒识 unknown 用于表达输入超出已知类别或模型信心不足；它不等于发现恶意流量。分类结果应携带执行后端和模型版本，并与确定性特征证据共同进入候选筛选。
- `KB-1261a365d7c6dba7` UDP 会话与双向流量: UDP 会话特征应结合包数、字节数、持续时间和双向比例解释。BALANCED_EXCHANGE 表示双向交换信号；业务同步、实时通信也可能出现类似观测。请关联资产角色与业务时段，不按单个端口直接判定协议。
- `KB-7de8fb605796915e` 引用与人工复核: 调查建议 INVESTIGATE 应引用当前会话的证据 ID，并核对证据强度和会话归属。知识文档只提供解释背景，不证明当前会话具备文档描述的行为。证据不足时保留 UNKNOWN，并列出需要人工核实的资产、业务用途和历史连接。

**Human rubric (0-2 each; leave evidence in notes)**

- [ ] Faithfulness: __ / 2
- [ ] Coverage: __ / 2
- [ ] Boundary and uncertainty: __ / 2
- [ ] Actionability: __ / 2
- [ ] Abstention correctness: __ / 2 or N/A
- Reviewer: __
- Notes: __

## A05: 证据不足时研判报告应该怎么写，还需要人工核实什么？

**Expected behavior:** ANSWER
**Observed status:** EXTRACTIVE

**Answer**

调查建议 INVESTIGATE 应引用当前会话的证据 ID，并核对证据强度和会话归属。知识文档只提供解释背景，不证明当前会话具备文档描述的行为。证据不足时保留 UNKNOWN，并列出需要人工核实的资产、业务用途和历史连接。

LONG_SESSION 长会话只说明持续时间触及配置阈值。周期性连接还应检查时间间隔、抖动和重复次数。阈值属于可调整策略，报告应保留观测值、阈值、规则版本与证据 ID，便于复查触发原因。

**Retrieved sources**

- `KB-7de8fb605796915e` 引用与人工复核: 调查建议 INVESTIGATE 应引用当前会话的证据 ID，并核对证据强度和会话归属。知识文档只提供解释背景，不证明当前会话具备文档描述的行为。证据不足时保留 UNKNOWN，并列出需要人工核实的资产、业务用途和历史连接。
- `KB-28da04190972691e` 长会话与周期性: LONG_SESSION 长会话只说明持续时间触及配置阈值。周期性连接还应检查时间间隔、抖动和重复次数。阈值属于可调整策略，报告应保留观测值、阈值、规则版本与证据 ID，便于复查触发原因。
- `KB-1f3b587c6c36b2a0` 序列分类与开放集拒识: 序列编码分类器输出类别预测。开放集拒识 unknown 用于表达输入超出已知类别或模型信心不足；它不等于发现恶意流量。分类结果应携带执行后端和模型版本，并与确定性特征证据共同进入候选筛选。
- `KB-c9a7f7bac49a9c03` 调查候选不是恶意结论: 调查候选 candidate 表示需要复核。长会话 LONG_SESSION 与双向均衡 BALANCED_EXCHANGE 可以作为调查线索，但不能单独证明 VPN、攻击或恶意通信。观察到的事实、模型预测与知识参考必须分别记录。

**Human rubric (0-2 each; leave evidence in notes)**

- [ ] Faithfulness: __ / 2
- [ ] Coverage: __ / 2
- [ ] Boundary and uncertainty: __ / 2
- [ ] Actionability: __ / 2
- [ ] Abstention correctness: __ / 2 or N/A
- Reviewer: __
- Notes: __

## A06: WireGuard 握手消息的固定字段偏移是多少？

**Expected behavior:** ABSTAIN
**Observed status:** NO_SOURCES

**Answer**

(abstained)

**Retrieved sources**

- None

**Human rubric (0-2 each; leave evidence in notes)**

- [ ] Faithfulness: __ / 2
- [ ] Coverage: __ / 2
- [ ] Boundary and uncertainty: __ / 2
- [ ] Actionability: __ / 2
- [ ] Abstention correctness: __ / 2 or N/A
- Reviewer: __
- Notes: __

## A07: 明天天气怎么样？

**Expected behavior:** ABSTAIN
**Observed status:** NO_SOURCES

**Answer**

(abstained)

**Retrieved sources**

- None

**Human rubric (0-2 each; leave evidence in notes)**

- [ ] Faithfulness: __ / 2
- [ ] Coverage: __ / 2
- [ ] Boundary and uncertainty: __ / 2
- [ ] Actionability: __ / 2
- [ ] Abstention correctness: __ / 2 or N/A
- Reviewer: __
- Notes: __
