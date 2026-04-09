<template>
  <div class="table-wrap">
    <n-data-table
      :columns="columns"
      :data="papers"
      :loading="loading"
      :pagination="pagination"
      :row-key="(row: any) => row.id"
      @update:page="$emit('page-change', $event)"
      :bordered="false"
      striped
    />
  </div>
</template>

<script setup lang="ts">
import { h } from 'vue'
import { NDataTable, NTag, NEllipsis } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'

defineProps<{
  papers: any[]
  loading: boolean
  pagination: { page: number; pageSize: number; pageCount?: number }
}>()

defineEmits<{ 'page-change': [page: number] }>()

const confColors: Record<string, string> = {
  NeurIPS: '#f0a030', ICLR: '#4ecdc4', ICML: '#e8637a',
  ACL: '#7eb5f0', EMNLP: '#b07ef0', AAAI: '#63e2b7',
  IJCAI: '#f0e070', KDD: '#f07e7e', NAACL: '#70c0f0', WWW: '#c0c0c0',
}

const columns: DataTableColumns = [
  {
    title: '标题',
    key: 'title',
    minWidth: 300,
    render(row: any) {
      return h(NEllipsis, { lineClamp: 2, style: 'font-weight: 500; color: var(--text-primary);' }, { default: () => row.title })
    },
  },
  {
    title: '年份',
    key: 'year',
    width: 70,
    render(row: any) {
      return h('span', { style: 'font-family: var(--font-mono); font-size: 12.5px; color: var(--text-secondary);' }, String(row.year))
    },
  },
  {
    title: '会议',
    key: 'conference',
    width: 100,
    render(row: any) {
      if (!row.conference) return ''
      const color = confColors[row.conference] || '#888'
      return h(NTag, {
        size: 'small',
        bordered: false,
        style: `background: ${color}18; color: ${color}; font-size: 11.5px; font-weight: 600;`,
      }, { default: () => row.conference })
    },
  },
  {
    title: '引用',
    key: 'citations',
    width: 80,
    sorter: 'default',
    render(row: any) {
      return h('span', { style: 'font-family: var(--font-mono); font-size: 12.5px; color: var(--accent-amber);' }, row.citations?.toLocaleString() || '0')
    },
  },
  {
    title: '摘要',
    key: 'abstract',
    render(row: any) {
      return h(NEllipsis, { lineClamp: 2, style: 'font-size: 12.5px; color: var(--text-muted); line-height: 1.5;' }, { default: () => row.abstract || '' })
    },
  },
]
</script>

<style scoped>
.table-wrap {
  padding: 0 24px 24px;
  flex: 1;
  overflow: auto;
}
</style>
