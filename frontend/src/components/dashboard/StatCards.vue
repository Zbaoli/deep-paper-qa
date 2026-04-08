<template>
  <div style="display: flex; gap: 16px; padding: 16px; flex-wrap: wrap;">
    <n-card size="small" style="flex: 1; min-width: 200px;">
      <n-statistic label="总论文数" :value="totalPapers" />
    </n-card>
    <n-card size="small" style="flex: 1; min-width: 200px;">
      <n-statistic label="会议数" :value="conferenceCount" />
    </n-card>
    <n-card size="small" style="flex: 1; min-width: 200px;">
      <n-statistic label="年份跨度" :value="yearRange" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { NCard, NStatistic } from 'naive-ui'

defineProps<{
  totalPapers: number
  conferenceCount: number
  yearRange: string
}>()
</script>
