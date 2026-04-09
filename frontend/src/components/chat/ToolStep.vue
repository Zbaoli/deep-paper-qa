<template>
  <div class="tool-step fade-in-up">
    <div class="tool-header" @click="expanded = !expanded">
      <span class="tool-status">{{ step.output ? '✓' : '⏳' }}</span>
      <span class="tool-name">{{ step.tool }}</span>
      <span v-if="step.durationMs" class="tool-duration">{{ step.durationMs }}ms</span>
      <span class="tool-chevron" :class="{ open: expanded }">›</span>
    </div>
    <div v-if="expanded" class="tool-body">
      <div class="tool-section">
        <span class="tool-label">输入</span>
        <pre class="tool-code">{{ inputStr }}</pre>
      </div>
      <div v-if="step.output" class="tool-section">
        <span class="tool-label">输出</span>
        <pre class="tool-code">{{ step.output }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ToolStep as ToolStepType } from '../../stores/chat'

const props = defineProps<{ step: ToolStepType }>()
const expanded = ref(false)

const inputStr = computed(() => {
  try {
    return JSON.stringify(props.step.input, null, 2)
  } catch {
    return String(props.step.input)
  }
})
</script>

<style scoped>
.tool-step {
  margin: 6px 0;
  border-radius: var(--radius-md);
  border: 1px solid var(--glass-border);
  overflow: hidden;
  font-size: 13px;
}
.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  background: rgba(255, 255, 255, 0.02);
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}
.tool-header:hover {
  background: rgba(255, 255, 255, 0.04);
}
.tool-status {
  font-size: 12px;
}
.tool-name {
  font-family: var(--font-mono);
  font-size: 12.5px;
  color: var(--accent-cyan);
}
.tool-duration {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.tool-chevron {
  font-size: 16px;
  color: var(--text-muted);
  transition: transform 0.2s;
}
.tool-chevron.open {
  transform: rotate(90deg);
}
.tool-body {
  padding: 10px 12px;
  border-top: 1px solid var(--glass-border);
}
.tool-section {
  margin-bottom: 8px;
}
.tool-section:last-child {
  margin-bottom: 0;
}
.tool-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}
.tool-code {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
  background: rgba(0, 0, 0, 0.2);
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  max-height: 160px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
</style>
