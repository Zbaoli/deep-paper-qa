<template>
  <div style="display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid rgba(255,255,255,0.1);">
    <n-input
      v-model:value="inputText"
      type="textarea"
      :autosize="{ minRows: 1, maxRows: 4 }"
      placeholder="输入问题..."
      @keydown.enter.exact.prevent="handleSend"
      :disabled="isStreaming"
    />
    <n-button type="primary" :disabled="!inputText.trim() || isStreaming" @click="handleSend">
      发送
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NInput, NButton } from 'naive-ui'
import { useChatStore } from '../../stores/chat'

const store = useChatStore()
const inputText = ref('')
const isStreaming = computed(() => store.isStreaming)

const emit = defineEmits<{ send: [content: string] }>()

function handleSend() {
  const text = inputText.value.trim()
  if (!text || store.isStreaming) return
  emit('send', text)
  inputText.value = ''
}
</script>
