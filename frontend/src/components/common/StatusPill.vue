<template><span class="status-pill" :class="tone"><i />{{ labels[status] || status || '未确定' }}</span></template>
<script setup>
import { computed } from "vue";
const props = defineProps({ status: String });
const tone = computed(() => ({ SUCCESS: 'success', COMPLETED: 'success', PROCESSING: 'active', WAITING: 'muted', FAILED: 'danger', CANDIDATE: 'warning', OBSERVE: 'muted', PASS: 'muted', UNKNOWN: 'warning' })[props.status] || 'muted');
const labels = { SUCCESS: '已完成', COMPLETED: '已完成', PROCESSING: '分析中', WAITING: '等待中', FAILED: '执行失败', CANCELED: '已取消', CANDIDATE: '调查候选', OBSERVE: '继续观察', PASS: '未触发', UNKNOWN: '待人工复核' };
</script>
