<template>
  <div style="display: flex; justify-content: flex-end; padding: 8px 16px;">
    <div style="max-width: 70%; background: #2080f0; color: white; padding: 10px 14px; border-radius: 12px 12px 2px 12px; white-space: pre-wrap;">
      {{ content }}
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ content: string }>()
</script>
