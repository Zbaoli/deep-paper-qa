<template>
  <div class="filter-bar">
    <div class="filter-row">
      <div class="search-wrap">
        <n-input
          v-model:value="query"
          placeholder="搜索论文标题、摘要..."
          clearable
          @keydown.enter="handleSearch"
        >
          <template #prefix>
            <span style="color: var(--text-muted); font-size: 14px;">⌕</span>
          </template>
        </n-input>
      </div>
      <n-select
        v-model:value="year"
        placeholder="年份"
        clearable
        :options="yearOptions"
        style="width: 110px;"
      />
      <n-select
        v-model:value="conference"
        placeholder="会议"
        clearable
        :options="conferenceOptions"
        style="width: 130px;"
      />
      <button class="search-btn" @click="handleSearch">检索</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NInput, NSelect } from 'naive-ui'

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

<style scoped>
.filter-bar {
  padding: 20px 24px 12px;
}
.filter-row {
  display: flex;
  gap: 10px;
  align-items: center;
  max-width: 900px;
}
.search-wrap {
  flex: 1;
}
.search-btn {
  padding: 0 20px;
  height: 34px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--accent-amber);
  color: #080c18;
  font-family: var(--font-body);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.search-btn:hover {
  background: #f5b550;
}
</style>
