<template>
  <div style="display: flex; gap: 16px; padding: 0 16px 16px; flex-wrap: wrap;">
    <n-card title="年度论文数量" style="flex: 1; min-width: 400px;">
      <v-chart :option="yearChartOption" style="height: 350px;" autoresize />
    </n-card>
    <n-card title="各会议论文数量" style="flex: 1; min-width: 400px;">
      <v-chart :option="confChartOption" style="height: 350px;" autoresize />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NCard } from 'naive-ui'
import VChart from 'vue-echarts'
import 'echarts'

const props = defineProps<{
  byYear: { year: number; count: number }[]
  byConference: { conference: string; count: number }[]
}>()

const yearChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: props.byYear.map(d => String(d.year)),
    axisLabel: { color: '#aaa' },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#aaa' },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
  },
  series: [{
    type: 'bar',
    data: props.byYear.map(d => d.count),
    itemStyle: { color: '#2080f0' },
  }],
  backgroundColor: 'transparent',
}))

const confChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: props.byConference.map(d => d.conference),
    axisLabel: { color: '#aaa', rotate: 30 },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#aaa' },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
  },
  series: [{
    type: 'bar',
    data: props.byConference.map(d => d.count),
    itemStyle: { color: '#63e2b7' },
  }],
  backgroundColor: 'transparent',
}))
</script>
