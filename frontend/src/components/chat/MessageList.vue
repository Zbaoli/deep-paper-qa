<template>
  <div ref="listRef" class="message-list">
    <div v-if="messages.length === 0" class="empty-state">
      <div class="empty-icon">◈</div>
      <h2 class="empty-title">Deep Paper QA</h2>
      <p class="empty-desc">AI 论文研究助手 · 81,913 篇顶会论文 · 2020—2025</p>
      <div class="starter-grid">
        <button class="starter-card" @click="$emit('send', '2024年NeurIPS收录了多少篇论文？')">
          <span class="starter-icon">📊</span>
          <span>会议论文统计</span>
        </button>
        <button class="starter-card" @click="$emit('send', '推荐一些高引用的大语言模型论文')">
          <span class="starter-icon">📄</span>
          <span>高引论文推荐</span>
        </button>
        <button class="starter-card" @click="$emit('send', '调研 2023-2025 年 RAG 的研究进展')">
          <span class="starter-icon">🔬</span>
          <span>深度调研</span>
        </button>
        <button class="starter-card" @click="$emit('send', 'RAG 近三年的发展趋势怎么样？')">
          <span class="starter-icon">📈</span>
          <span>趋势分析</span>
        </button>
      </div>
    </div>
    <div class="messages-container">
      <template v-for="msg in messages" :key="msg.id">
        <UserMessage v-if="msg.role === 'user'" :content="msg.content" />
        <AiMessage v-else :message="msg" @reply="$emit('reply', $event)" />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { ChatMessage } from '../../stores/chat'
import UserMessage from './UserMessage.vue'
import AiMessage from './AiMessage.vue'

const props = defineProps<{ messages: ChatMessage[] }>()
defineEmits<{ reply: [text: string]; send: [content: string] }>()

const listRef = ref<HTMLDivElement>()

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

<style scoped>
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}
.messages-container {
  max-width: 820px;
  margin: 0 auto;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
  padding: 40px 24px;
}
.empty-icon {
  font-size: 48px;
  color: var(--accent-amber);
  margin-bottom: 16px;
  opacity: 0.7;
}
.empty-title {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 400;
  color: var(--text-primary);
  margin-bottom: 8px;
}
.empty-desc {
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 32px;
}
.starter-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  width: 100%;
  max-width: 420px;
}
.starter-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 13px;
  font-family: var(--font-body);
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}
.starter-card:hover {
  background: var(--bg-elevated);
  border-color: var(--glass-border-hover);
  color: var(--text-primary);
}
.starter-icon {
  font-size: 16px;
}
</style>
