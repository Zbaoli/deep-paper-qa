<template>
  <div style="height: 100%; overflow-y: auto;">
    <n-spin :show="loading" style="min-height: 200px;">
      <StatCards
        :total-papers="stats.total_papers"
        :conference-count="stats.by_conference.length"
        :year-range="yearRange"
      />
      <TrendChart
        :by-year="stats.by_year"
        :by-conference="stats.by_conference"
      />
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NSpin } from 'naive-ui'
import { fetchApi } from '../composables/useApi'
import StatCards from '../components/dashboard/StatCards.vue'
import TrendChart from '../components/dashboard/TrendChart.vue'

interface StatsData {
  total_papers: number
  by_year: { year: number; count: number }[]
  by_conference: { conference: string; count: number }[]
}

const loading = ref(true)
const stats = ref<StatsData>({
  total_papers: 0,
  by_year: [],
  by_conference: [],
})

const yearRange = computed(() => {
  const years = stats.value.by_year.map(d => d.year)
  if (years.length === 0) return '-'
  return `${Math.min(...years)} — ${Math.max(...years)}`
})

onMounted(async () => {
  try {
    stats.value = await fetchApi<StatsData>('/stats')
  } catch (err) {
    console.error('Failed to load stats:', err)
  } finally {
    loading.value = false
  }
})
</script>
