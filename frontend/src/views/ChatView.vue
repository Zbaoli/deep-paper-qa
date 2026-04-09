<template>
  <div style="display: flex; flex-direction: column; height: 100%;">
    <MessageList :messages="store.messages" @reply="handleReply" @send="handleSend" />
    <ChatInput @send="handleSend" />
  </div>
</template>

<script setup lang="ts">
import { useChatStore } from '../stores/chat'
import { useChat } from '../composables/useChat'
import MessageList from '../components/chat/MessageList.vue'
import ChatInput from '../components/chat/ChatInput.vue'

const store = useChatStore()
const { sendMessage, submitReply } = useChat()

function handleSend(content: string) {
  sendMessage(content)
}

function handleReply(text: string) {
  submitReply(text)
}
</script>
