<template>
  <div class="charts-row">
    <div class="chart-card glass-card">
      <div class="chart-title">年度论文数量</div>
      <v-chart :option="yearChartOption" style="height: 320px;" autoresize />
    </div>
    <div class="chart-card glass-card">
      <div class="chart-title">各会议论文数量</div>
      <v-chart :option="confChartOption" style="height: 320px;" autoresize />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import 'echarts'

const props = defineProps<{
  byYear: { year: number; count: number }[]
  byConference: { conference: string; count: number }[]
}>()

const yearChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(14, 20, 40, 0.9)',
    borderColor: 'rgba(255,255,255,0.08)',
    textStyle: { color: '#e8eaf0', fontFamily: 'DM Sans', fontSize: 12 },
  },
  grid: { left: 50, right: 20, top: 20, bottom: 30 },
  xAxis: {
    type: 'category',
    data: props.byYear.map(d => String(d.year)),
    axisLabel: { color: '#505870', fontFamily: 'JetBrains Mono', fontSize: 11 },
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#505870', fontFamily: 'JetBrains Mono', fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } },
  },
  series: [{
    type: 'bar',
    data: props.byYear.map(d => d.count),
    itemStyle: {
      color: {
        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: '#f0a030' },
          { offset: 1, color: 'rgba(240, 160, 48, 0.3)' },
        ],
      },
      borderRadius: [4, 4, 0, 0],
    },
    barWidth: '55%',
  }],
  backgroundColor: 'transparent',
}))

const confColors = [
  '#f0a030', '#4ecdc4', '#e8637a', '#7eb5f0', '#b07ef0',
  '#63e2b7', '#f0e070', '#f07e7e', '#70c0f0', '#c0c0c0',
]

const confChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(14, 20, 40, 0.9)',
    borderColor: 'rgba(255,255,255,0.08)',
    textStyle: { color: '#e8eaf0', fontFamily: 'DM Sans', fontSize: 12 },
  },
  grid: { left: 50, right: 20, top: 20, bottom: 50 },
  xAxis: {
    type: 'category',
    data: props.byConference.map(d => d.conference),
    axisLabel: { color: '#505870', fontFamily: 'DM Sans', fontSize: 11, rotate: 25 },
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#505870', fontFamily: 'JetBrains Mono', fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } },
  },
  series: [{
    type: 'bar',
    data: props.byConference.map((d, i) => ({
      value: d.count,
      itemStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: confColors[i % confColors.length] },
            { offset: 1, color: confColors[i % confColors.length] + '30' },
          ],
        },
        borderRadius: [4, 4, 0, 0],
      },
    })),
    barWidth: '60%',
  }],
  backgroundColor: 'transparent',
}))
</script>

<style scoped>
.charts-row {
  display: flex;
  gap: 16px;
  padding: 0 24px 24px;
}
.chart-card {
  flex: 1;
  min-width: 0;
  padding: 20px;
}
.chart-title {
  font-family: var(--font-display);
  font-size: 16px;
  color: var(--text-primary);
  margin-bottom: 12px;
}
</style>
