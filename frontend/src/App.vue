<template>
  <n-config-provider :theme="darkTheme" :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <div class="app-shell">
      <!-- Header -->
      <header class="app-header">
        <div class="header-brand" @click="router.push('/chat')">
          <span class="brand-icon">◈</span>
          <span class="brand-text">Deep Paper QA</span>
        </div>
        <nav class="header-nav">
          <button
            v-for="item in navItems"
            :key="item.key"
            :class="['nav-pill', { active: currentRoute === item.key }]"
            @click="router.push({ name: item.key })"
          >
            <span class="nav-icon">{{ item.icon }}</span>
            {{ item.label }}
          </button>
        </nav>
        <div class="header-meta">
          <span class="meta-badge">81,913 papers</span>
        </div>
      </header>

      <!-- Content -->
      <main class="app-content">
        <router-view />
      </main>
    </div>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NConfigProvider, darkTheme } from 'naive-ui'
import { zhCN, dateZhCN } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'

const router = useRouter()
const route = useRoute()

const currentRoute = computed(() => route.name as string)

const navItems = [
  { label: '对话', key: 'chat', icon: '◉' },
  { label: '检索', key: 'explore', icon: '⊞' },
  { label: '看板', key: 'dashboard', icon: '◧' },
]

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#f0a030',
    primaryColorHover: '#f5b550',
    primaryColorPressed: '#d89020',
    bodyColor: '#080c18',
    cardColor: 'rgba(18, 26, 50, 0.65)',
    borderColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: '10px',
    fontFamily: "'DM Sans', -apple-system, sans-serif",
    fontSize: '14px',
  },
  Input: {
    color: 'rgba(255, 255, 255, 0.04)',
    colorFocus: 'rgba(255, 255, 255, 0.06)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderFocus: '1px solid rgba(240, 160, 48, 0.4)',
    borderRadius: '10px',
  },
  Button: {
    borderRadiusMedium: '10px',
    borderRadiusSmall: '8px',
  },
  Card: {
    borderRadius: '16px',
    color: 'rgba(18, 26, 50, 0.65)',
    borderColor: 'rgba(255, 255, 255, 0.06)',
  },
  Tag: {
    borderRadius: '6px',
  },
}
</script>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-deep);
}

.app-header {
  display: flex;
  align-items: center;
  height: 56px;
  padding: 0 24px;
  background: rgba(8, 12, 24, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--glass-border);
  gap: 24px;
  flex-shrink: 0;
  z-index: 100;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}
.brand-icon {
  font-size: 20px;
  color: var(--accent-amber);
}
.brand-text {
  font-family: var(--font-display);
  font-size: 18px;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.header-nav {
  display: flex;
  gap: 4px;
  flex: 1;
}

.nav-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border: none;
  border-radius: 20px;
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-body);
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}
.nav-pill:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}
.nav-pill.active {
  background: var(--accent-amber-dim);
  color: var(--accent-amber);
}
.nav-icon {
  font-size: 14px;
  opacity: 0.7;
}

.header-meta {
  margin-left: auto;
}
.meta-badge {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.04);
  padding: 4px 10px;
  border-radius: 12px;
  letter-spacing: 0.02em;
}

.app-content {
  flex: 1;
  overflow: hidden;
}
</style>
