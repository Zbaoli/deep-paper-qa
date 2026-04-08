<template>
  <n-collapse style="margin: 4px 0;">
    <n-collapse-item :title="title" :name="step.runId">
      <div style="font-size: 12px;">
        <div><strong>输入：</strong></div>
        <n-code :code="inputStr" language="json" style="max-height: 200px; overflow: auto;" />
        <div v-if="step.output" style="margin-top: 8px;">
          <strong>输出：</strong>
          <n-code :code="step.output" style="max-height: 200px; overflow: auto;" />
        </div>
        <div v-if="step.durationMs" style="margin-top: 4px; color: #999;">
          耗时: {{ step.durationMs }}ms
        </div>
      </div>
    </n-collapse-item>
  </n-collapse>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NCollapse, NCollapseItem, NCode } from 'naive-ui'
import type { ToolStep as ToolStepType } from '../../stores/chat'

const props = defineProps<{ step: ToolStepType }>()

const title = computed(() => {
  const icon = props.step.output ? '✓' : '⏳'
  return `${icon} ${props.step.tool}`
})

const inputStr = computed(() => {
  try {
    return JSON.stringify(props.step.input, null, 2)
  } catch {
    return String(props.step.input)
  }
})
</script>
