<template>
  <el-card class="span-2" shadow="never">
    <template #header>
      <div class="card-title">分析链路与研发原则</div>
    </template>

    <el-collapse>
      <el-collapse-item name="pipeline" title="主链路说明">
        <ul class="plain-list">
          <li>Java 主服务负责任务创建、状态流转、结果回写和产物下载接口。</li>
          <li>Python 分析服务负责 pcap 解析、特征提取、模型推理和报告生成。</li>
          <li>结果统一沉淀为 <code>summary</code>、<code>report</code> 和 <code>predicted_flows</code> 三类产物，由前端按任务消费。</li>
        </ul>
      </el-collapse-item>

      <el-collapse-item name="model" title="当前模型定位">
        <ul class="plain-list">
          <li><code>SEQUENCE_ENCODER</code> 现在是平台主路线，用来承接增强识别、知识增强和后续正式模型替换。</li>
          <li><code>FEATURE_RULES</code> 保留为兼容与对照能力，用于兜底、历史结果复用和同样本双路线比较。</li>
          <li>大模型只负责解释、归纳和报告生成，不替代底层检测判定。</li>
        </ul>
      </el-collapse-item>

      <el-collapse-item name="principle" title="研发原则">
        <ul class="plain-list">
          <li>先把主链路做通，再逐步增强，而不是一开始就堆满工程化组件。</li>
          <li>明确保留阶段边界，例如兼容 smoke 模型、fallback 路径和外部接口波动。</li>
          <li>所有增强能力都要能回到结构化证据，避免只剩一层“会说话”的展示。</li>
        </ul>
      </el-collapse-item>
    </el-collapse>
  </el-card>
</template>

<script setup>
</script>
