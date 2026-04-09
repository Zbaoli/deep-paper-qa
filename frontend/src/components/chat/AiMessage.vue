<template>
  <div class="ai-msg fade-in-up">
    <!-- 路由标签 -->
    <span v-if="message.categoryLabel" class="category-tag">{{ message.categoryLabel }}</span>

    <!-- Tool steps -->
    <ToolStep v-for="step in message.toolSteps" :key="step.runId" :step="step" />

    <!-- 消息内容 (Markdown) -->
    <div
      v-if="message.content"
      class="markdown-body"
      :class="{ 'typing-cursor': message.loading }"
      v-html="renderedContent"
    />

    <!-- 图表 -->
    <div v-for="(chart, idx) in message.charts" :key="idx" class="chart-container glass-card">
      <v-chart
        v-if="chart.type === 'echarts' && chart.option"
        :option="chart.option"
        style="height: 350px;"
        autoresize
      />
    </div>

    <!-- ask_user 卡片 -->
    <AskUserCard
      v-if="message.askUser"
      :ask-user="message.askUser"
      @reply="$emit('reply', $event)"
    />

    <!-- 加载指示器 -->
    <div v-if="message.loading && !message.content" class="loading-dots">
      <span></span><span></span><span></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import 'echarts'
import VChart from 'vue-echarts'
import type { ChatMessage } from '../../stores/chat'
import ToolStep from './ToolStep.vue'
import AskUserCard from './AskUserCard.vue'

const props = defineProps<{ message: ChatMessage }>()
defineEmits<{ reply: [text: string] }>()

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const renderedContent = computed(() => md.render(props.message.content))
</script>

<style scoped>
.ai-msg {
  padding: 8px 24px;
  max-width: 760px;
}
.category-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent-amber);
  background: var(--accent-amber-dim);
  padding: 3px 10px;
  border-radius: 12px;
  margin-bottom: 8px;
  letter-spacing: 0.02em;
}
.chart-container {
  margin: 14px 0;
  padding: 16px;
}
.loading-dots {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}
.loading-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-amber);
  animation: dotPulse 1.2s infinite ease-in-out;
}
.loading-dots span:nth-child(2) { animation-delay: 0.15s; }
.loading-dots span:nth-child(3) { animation-delay: 0.3s; }
@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}
</style>
