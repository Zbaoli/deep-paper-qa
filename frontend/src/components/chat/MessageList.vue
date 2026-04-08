<template>
  <div ref="listRef" style="flex: 1; overflow-y: auto; padding: 8px 0;">
    <template v-for="msg in messages" :key="msg.id">
      <UserMessage v-if="msg.role === 'user'" :content="msg.content" />
      <AiMessage v-else :message="msg" @reply="$emit('reply', $event)" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { ChatMessage } from '../../stores/chat'
import UserMessage from './UserMessage.vue'
import AiMessage from './AiMessage.vue'

const props = defineProps<{ messages: ChatMessage[] }>()
defineEmits<{ reply: [text: string] }>()

const listRef = ref<HTMLDivElement>()

// 自动滚动到底部
watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  }
)
</script>
