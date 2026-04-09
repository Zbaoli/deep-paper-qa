<template>
  <div class="user-msg fade-in-up">
    <div class="user-bubble">{{ content }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ content: string }>()
</script>

<style scoped>
.user-msg {
  display: flex;
  justify-content: flex-end;
  padding: 6px 24px;
}
.user-bubble {
  max-width: 65%;
  background: linear-gradient(135deg, rgba(240,160,48,0.2), rgba(240,160,48,0.08));
  border: 1px solid rgba(240, 160, 48, 0.2);
  color: var(--text-primary);
  padding: 10px 16px;
  border-radius: 16px 16px 4px 16px;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
}
</style>
