<template>
  <div style="padding: 8px 16px;">
    <!-- 路由标签 -->
    <n-tag v-if="message.categoryLabel" size="small" type="info" style="margin-bottom: 6px;">
      {{ message.categoryLabel }}
    </n-tag>

    <!-- Tool steps -->
    <ToolStep v-for="step in message.toolSteps" :key="step.runId" :step="step" />

    <!-- 消息内容 (Markdown) -->
    <div
      v-if="message.content"
      class="markdown-body"
      style="line-height: 1.7;"
      v-html="renderedContent"
    />

    <!-- 图表 -->
    <div v-for="(chart, idx) in message.charts" :key="idx" style="margin: 12px 0;">
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
    <n-spin v-if="message.loading && !message.content" size="small" style="margin: 8px 0;" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NTag, NSpin } from 'naive-ui'
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
