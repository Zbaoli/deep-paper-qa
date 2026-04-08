<template>
  <div style="height: 100%; display: flex; flex-direction: column;">
    <PaperFilter @search="handleSearch" />
    <PaperTable
      :papers="papers"
      :loading="loading"
      :pagination="{ page, pageSize: 20 }"
      @page-change="handlePageChange"
      style="flex: 1;"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchApi } from '../composables/useApi'
import PaperFilter from '../components/explore/PaperFilter.vue'
import PaperTable from '../components/explore/PaperTable.vue'

const papers = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const currentParams = ref<{ q: string; year?: number; conference?: string }>({ q: '' })

async function loadPapers() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (currentParams.value.q) params.set('q', currentParams.value.q)
    if (currentParams.value.year) params.set('year', String(currentParams.value.year))
    if (currentParams.value.conference) params.set('conference', currentParams.value.conference)
    params.set('page', String(page.value))
    params.set('page_size', '20')

    const data = await fetchApi<{ papers: any[] }>(`/papers?${params}`)
    papers.value = data.papers
  } catch (err) {
    console.error('Failed to load papers:', err)
  } finally {
    loading.value = false
  }
}

function handleSearch(params: { q: string; year?: number; conference?: string }) {
  currentParams.value = params
  page.value = 1
  loadPapers()
}

function handlePageChange(p: number) {
  page.value = p
  loadPapers()
}

onMounted(loadPapers)
</script>
