<template>
  <div style="display: flex; gap: 12px; padding: 16px; flex-wrap: wrap;">
    <n-input
      v-model:value="query"
      placeholder="搜索论文..."
      clearable
      style="flex: 1; min-width: 200px;"
      @keydown.enter="handleSearch"
    />
    <n-select
      v-model:value="year"
      placeholder="年份"
      clearable
      :options="yearOptions"
      style="width: 120px;"
    />
    <n-select
      v-model:value="conference"
      placeholder="会议"
      clearable
      :options="conferenceOptions"
      style="width: 140px;"
    />
    <n-button type="primary" @click="handleSearch">搜索</n-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NInput, NSelect, NButton } from 'naive-ui'

const emit = defineEmits<{
  search: [params: { q: string; year?: number; conference?: string }]
}>()

const query = ref('')
const year = ref<number | null>(null)
const conference = ref<string | null>(null)

const yearOptions = [2020, 2021, 2022, 2023, 2024, 2025].map(y => ({ label: String(y), value: y }))

const conferenceOptions = [
  'ACL', 'EMNLP', 'NeurIPS', 'ICLR', 'ICML', 'AAAI', 'IJCAI', 'KDD', 'NAACL', 'WWW',
].map(c => ({ label: c, value: c }))

function handleSearch() {
  emit('search', {
    q: query.value,
    year: year.value ?? undefined,
    conference: conference.value ?? undefined,
  })
}
</script>
