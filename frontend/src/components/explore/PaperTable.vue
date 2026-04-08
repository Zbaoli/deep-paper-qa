<template>
  <n-data-table
    :columns="columns"
    :data="papers"
    :loading="loading"
    :pagination="pagination"
    :row-key="(row: any) => row.id"
    @update:page="$emit('page-change', $event)"
    style="padding: 0 16px;"
  />
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

const columns: DataTableColumns = [
  {
    title: '标题',
    key: 'title',
    width: 400,
    render(row: any) {
      return h(NEllipsis, { lineClamp: 2 }, { default: () => row.title })
    },
  },
  { title: '年份', key: 'year', width: 80 },
  {
    title: '会议',
    key: 'conference',
    width: 100,
    render(row: any) {
      return row.conference ? h(NTag, { size: 'small', type: 'info' }, { default: () => row.conference }) : ''
    },
  },
  { title: '引用', key: 'citations', width: 80, sorter: 'default' },
  {
    title: '摘要',
    key: 'abstract',
    render(row: any) {
      return h(NEllipsis, { lineClamp: 2, style: 'font-size: 12px; color: #999;' }, { default: () => row.abstract || '' })
    },
  },
]
</script>
