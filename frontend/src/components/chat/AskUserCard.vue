<template>
  <div class="ask-card glass-card fade-in-up">
    <div class="ask-summary">{{ askUser.summary }}</div>
    <div class="ask-divider"></div>
    <div class="ask-question">{{ askUser.question }}</div>
    <div class="ask-actions">
      <n-input v-model:value="replyText" placeholder="输入回复..." size="small" />
      <n-button type="primary" size="small" @click="handleReply">回复</n-button>
      <n-button size="small" quaternary @click="handleContinue">继续</n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NInput, NButton } from 'naive-ui'

const props = defineProps<{ askUser: { question: string; summary: string } }>()
const emit = defineEmits<{ reply: [text: string] }>()

const replyText = ref('')

function handleReply() {
  const text = replyText.value.trim() || '继续'
  emit('reply', text)
}

function handleContinue() {
  emit('reply', '继续')
}
</script>

<style scoped>
.ask-card {
  max-width: 520px;
  padding: 16px;
  margin: 10px 0;
}
.ask-summary {
  font-size: 13.5px;
  color: var(--text-secondary);
  white-space: pre-wrap;
  line-height: 1.6;
}
.ask-divider {
  height: 1px;
  background: var(--glass-border);
  margin: 12px 0;
}
.ask-question {
  font-weight: 600;
  color: var(--accent-amber);
  margin-bottom: 12px;
  font-size: 14px;
}
.ask-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
