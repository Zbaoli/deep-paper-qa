import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  category?: string
  categoryLabel?: string
  toolSteps?: ToolStep[]
  charts?: ChartData[]
  askUser?: { question: string; summary: string }
  loading?: boolean
}

export interface ToolStep {
  tool: string
  input: any
  output?: string
  durationMs?: number
  runId: string
}

export interface ChartData {
  type: 'echarts' | 'plotly'
  option?: Record<string, any>
  figure?: Record<string, any>
}

export interface Conversation {
  id: string
  file: string
  startedAt: string
  firstMessage: string
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const threadId = ref(crypto.randomUUID())
  const isStreaming = ref(false)
  const conversations = ref<Conversation[]>([])

  function addUserMessage(content: string) {
    messages.value.push({
      id: crypto.randomUUID(),
      role: 'user',
      content,
    })
  }

  function addAssistantMessage(): ChatMessage {
    const msg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      toolSteps: [],
      charts: [],
      loading: true,
    }
    messages.value.push(msg)
    return messages.value[messages.value.length - 1]
  }

  function currentAssistantMessage(): ChatMessage | undefined {
    const msgs = messages.value
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'assistant') return msgs[i]
    }
    return undefined
  }

  function newConversation() {
    messages.value = []
    threadId.value = crypto.randomUUID()
  }

  return {
    messages,
    threadId,
    isStreaming,
    conversations,
    addUserMessage,
    addAssistantMessage,
    currentAssistantMessage,
    newConversation,
  }
})
