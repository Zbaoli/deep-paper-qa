<template>
  <n-config-provider :theme="darkTheme" :locale="zhCN" :date-locale="dateZhCN">
    <n-layout style="height: 100vh">
      <n-layout-header bordered style="height: 48px; display: flex; align-items: center; padding: 0 20px; gap: 24px;">
        <n-text strong style="font-size: 16px; white-space: nowrap;">Deep Paper QA</n-text>
        <n-menu
          mode="horizontal"
          :value="currentRoute"
          :options="menuOptions"
          @update:value="handleMenuClick"
          style="flex: 1;"
        />
      </n-layout-header>
      <n-layout-content style="height: calc(100vh - 48px);">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NConfigProvider,
  NLayout,
  NLayoutHeader,
  NLayoutContent,
  NMenu,
  NText,
  darkTheme,
} from 'naive-ui'
import { zhCN, dateZhCN } from 'naive-ui'

const router = useRouter()
const route = useRoute()

const currentRoute = computed(() => route.name as string)

const menuOptions = [
  { label: '聊天', key: 'chat' },
  { label: '论文浏览', key: 'explore' },
  { label: '数据看板', key: 'dashboard' },
]

function handleMenuClick(key: string) {
  router.push({ name: key })
}
</script>
