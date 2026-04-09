<template>
  <div class="stats-row">
    <div class="stat-card glass-card">
      <div class="stat-label">总论文数</div>
      <div class="stat-value amber">{{ totalPapers.toLocaleString() }}</div>
    </div>
    <div class="stat-card glass-card">
      <div class="stat-label">收录会议</div>
      <div class="stat-value cyan">{{ conferenceCount }}</div>
    </div>
    <div class="stat-card glass-card">
      <div class="stat-label">年份跨度</div>
      <div class="stat-value">{{ yearRange }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  totalPapers: number
  conferenceCount: number
  yearRange: string
}>()
</script>

<style scoped>
.stats-row {
  display: flex;
  gap: 16px;
  padding: 20px 24px;
}
.stat-card {
  flex: 1;
  padding: 20px 24px;
}
.stat-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}
.stat-value {
  font-family: var(--font-display);
  font-size: 32px;
  color: var(--text-primary);
  line-height: 1.1;
}
.stat-value.amber { color: var(--accent-amber); }
.stat-value.cyan { color: var(--accent-cyan); }
</style>
