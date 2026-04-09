<template>
  <div class="chat-input-bar">
    <div class="input-container">
      <n-input
        v-model:value="inputText"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 4 }"
        placeholder="输入你的研究问题..."
        @keydown.enter.exact="handleKeydown"
        :disabled="isStreaming"
      />
      <button
        class="send-btn"
        :disabled="!inputText.trim() || isStreaming"
        @click="handleSend"
      >
        <span class="send-icon">↑</span>
      </button>
    </div>
    <div class="input-hint">按 Enter 发送 · 支持论文检索、统计分析、趋势追踪</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NInput } from 'naive-ui'
import { useChatStore } from '../../stores/chat'

const store = useChatStore()
const inputText = ref('')
const isStreaming = computed(() => store.isStreaming)

const emit = defineEmits<{ send: [content: string] }>()

function handleKeydown(e: KeyboardEvent) {
  if (e.isComposing) return
  e.preventDefault()
  handleSend()
}

function handleSend() {
  const text = inputText.value.trim()
  if (!text || store.isStreaming) return
  emit('send', text)
  inputText.value = ''
}
</script>

<style scoped>
.chat-input-bar {
  padding: 12px 24px 16px;
  background: linear-gradient(to top, var(--bg-deep), transparent);
}
.input-container {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  max-width: 760px;
  margin: 0 auto;
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  padding: 6px 6px 6px 14px;
  transition: border-color 0.2s;
}
.input-container:focus-within {
  border-color: rgba(240, 160, 48, 0.3);
}
.input-container :deep(.n-input) {
  --n-border: none !important;
  --n-border-hover: none !important;
  --n-border-focus: none !important;
  --n-color: transparent !important;
  --n-color-focus: transparent !important;
  --n-box-shadow-focus: none !important;
}
.send-btn {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: var(--accent-amber);
  color: #080c18;
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.send-btn:hover:not(:disabled) {
  background: #f5b550;
  transform: translateY(-1px);
}
.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.input-hint {
  text-align: center;
  font-size: 11.5px;
  color: var(--text-muted);
  margin-top: 8px;
}
</style>
