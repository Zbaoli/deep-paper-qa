import { useChatStore, type ToolStep, type ChartData, type ChatMessage } from '../stores/chat'

/**
 * 聊天核心 composable：连接到 POST /api/chat，处理 SSE 事件流
 */
export function useChat() {
  const store = useChatStore()

  /**
   * 发送用户消息，启动 SSE 流式接收
   * @param content - 用户输入内容
   */
  async function sendMessage(content: string) {
    if (!content.trim() || store.isStreaming) return

    store.addUserMessage(content)
    const assistantMsg = store.addAssistantMessage()
    store.isStreaming = true

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          thread_id: store.threadId,
        }),
      })

      if (!resp.ok || !resp.body) {
        assistantMsg.content = '请求失败，请重试。'
        assistantMsg.loading = false
        store.isStreaming = false
        return
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim()
          } else if (line.startsWith('data:')) {
            const dataStr = line.slice(5).trim()
            if (!dataStr) continue
            try {
              const data = JSON.parse(dataStr)
              handleEvent(currentEvent, data, assistantMsg)
            } catch {
              // 忽略 JSON 解析错误，继续处理后续事件
            }
          }
        }
      }
    } catch {
      assistantMsg.content += '\n\n连接中断，请重试。'
    } finally {
      assistantMsg.loading = false
      store.isStreaming = false
    }
  }

  /**
   * 处理单个 SSE 事件，更新助手消息状态
   * @param event - 事件类型
   * @param data - 事件数据
   * @param msg - 待更新的助手消息对象
   */
  function handleEvent(event: string, data: Record<string, unknown>, msg: ChatMessage) {
    switch (event) {
      case 'route':
        msg.category = data.category as string
        msg.categoryLabel = data.label as string
        break
      case 'tool_start':
        msg.toolSteps = msg.toolSteps || []
        msg.toolSteps.push({
          tool: data.tool as string,
          input: data.input,
          runId: data.run_id as string,
        } as ToolStep)
        break
      case 'tool_end':
        if (msg.toolSteps) {
          const step = msg.toolSteps.find((s: ToolStep) => s.runId === data.run_id)
          if (step) {
            step.output = data.output as string
            step.durationMs = data.duration_ms as number
          }
        }
        break
      case 'token':
        msg.content += data.content as string
        break
      case 'chart':
        msg.charts = msg.charts || []
        msg.charts.push({
          type: data.type as string,
          option: data.option,
          figure: data.figure,
        } as ChartData)
        break
      case 'ask_user':
        msg.askUser = {
          question: data.question as string,
          summary: data.summary as string,
        }
        break
      case 'done':
        msg.loading = false
        break
      case 'error':
        msg.content += `\n\n错误: ${data.message as string}`
        msg.loading = false
        break
    }
  }

  /**
   * 提交用户追问回复，清除当前消息的 askUser 状态
   * @param reply - 用户回复内容
   */
  async function submitReply(reply: string) {
    try {
      await fetch(`/api/chat/${store.threadId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reply }),
      })
      // 清除当前助手消息的追问状态
      const msg = store.currentAssistantMessage()
      if (msg) {
        msg.askUser = undefined
      }
    } catch (err) {
      console.error('Failed to submit reply:', err)
    }
  }

  return { sendMessage, submitReply }
}
