<template>
  <n-card size="small" style="margin: 8px 0; max-width: 500px;">
    <div style="margin-bottom: 8px; white-space: pre-wrap;">{{ askUser.summary }}</div>
    <n-divider style="margin: 8px 0;" />
    <div style="margin-bottom: 8px; font-weight: bold;">{{ askUser.question }}</div>
    <div style="display: flex; gap: 8px;">
      <n-input v-model:value="replyText" placeholder="输入回复..." size="small" />
      <n-button type="primary" size="small" @click="handleReply">回复</n-button>
      <n-button size="small" @click="handleContinue">继续</n-button>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NCard, NDivider, NInput, NButton } from 'naive-ui'

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
