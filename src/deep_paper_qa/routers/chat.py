"""聊天 API 路由：SSE 事件流 + ask_user 回复"""

import time

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from loguru import logger
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from deep_paper_qa.agent import build_graph
from deep_paper_qa.config import settings
from deep_paper_qa.conversation_logger import ConversationLogger
from deep_paper_qa.sse_events import sse
from deep_paper_qa.tools.ask_user import get_pending_question, submit_reply

router = APIRouter(tags=["chat"])

_graph = None
_conv_logger = ConversationLogger()


def _get_graph():
    """懒加载 graph（避免 import 时就构建）"""
    global _graph
    if _graph is None:
        _graph, _ = build_graph()
    return _graph


class ChatRequest(BaseModel):
    """聊天请求"""

    message: str
    thread_id: str


class ReplyRequest(BaseModel):
    """ask_user 回复请求"""

    reply: str


@router.post("/chat")
async def chat(req: ChatRequest) -> EventSourceResponse:
    """聊天 SSE 流"""

    async def event_stream():
        msg_start = time.monotonic()
        tool_call_count = 0
        tools_used: list[str] = []
        tool_timings: dict[str, tuple[str, float]] = {}

        try:
            graph = _get_graph()
            config = {
                "configurable": {"thread_id": req.thread_id},
                "recursion_limit": settings.agent_recursion_limit,
            }

            logger.info("API chat | thread={} | message={}", req.thread_id, req.message[:200])
            _conv_logger.log_user_message(req.thread_id, req.message)

            async for event in graph.astream_events(
                {"messages": [HumanMessage(content=req.message)]},
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")
                name = event.get("name", "")

                # 工具开始
                if kind == "on_tool_start":
                    run_id = event.get("run_id", "")
                    tool_input = event.get("data", {}).get("input", {})
                    tool_timings[run_id] = (name, time.monotonic())
                    tool_call_count += 1
                    if name not in tools_used:
                        tools_used.append(name)

                    _conv_logger.log_tool_start(req.thread_id, name, tool_input)

                    if name == "ask_user":
                        summary = tool_input.get("summary", "")
                        question = tool_input.get("question", "")
                        yield sse("ask_user", {"question": question, "summary": summary})
                    else:
                        yield sse("tool_start", {"tool": name, "input": tool_input, "run_id": run_id})

                # 工具结束
                elif kind == "on_tool_end":
                    run_id = event.get("run_id", "")
                    output = event.get("data", {}).get("output", "")
                    if hasattr(output, "content"):
                        output = output.content
                    output_str = str(output)

                    duration_ms = 0
                    tool_name = name
                    if run_id in tool_timings:
                        tool_name, start_t = tool_timings.pop(run_id)
                        duration_ms = int((time.monotonic() - start_t) * 1000)

                    _conv_logger.log_tool_end(req.thread_id, tool_name, duration_ms, output_str)

                    if tool_name != "ask_user":
                        yield sse("tool_end", {"tool": tool_name, "output": output_str[:500], "duration_ms": duration_ms, "run_id": run_id})

                # LLM 流式 token
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", None)
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield sse("token", {"content": chunk.content})

                # 工具内部通过 get_stream_writer() 发的 UI 事件
                elif kind == "on_custom_event":
                    payload = event.get("data", {})
                    if isinstance(payload, dict) and "event" in payload:
                        yield sse(payload["event"], payload.get("data", {}))

            total_ms = int((time.monotonic() - msg_start) * 1000)
            _conv_logger.log_agent_reply(req.thread_id, "", total_ms, tool_call_count, tools_used)
            yield sse("done", {"total_ms": total_ms, "tool_calls": tool_call_count})

        except Exception as e:
            logger.exception("API chat 异常 | thread={} | error={}", req.thread_id, e)
            yield sse("error", {"message": f"{type(e).__name__}: {e}"})
            yield sse("done", {"total_ms": int((time.monotonic() - msg_start) * 1000), "tool_calls": tool_call_count})

    return EventSourceResponse(event_stream())


@router.post("/chat/{thread_id}/reply")
async def reply(thread_id: str, req: ReplyRequest) -> dict[str, str]:
    """提交 ask_user 回复"""
    pending = get_pending_question(thread_id)
    if not pending:
        raise HTTPException(status_code=404, detail="没有等待中的问题")

    submit_reply(thread_id, req.reply)
    return {"status": "ok"}


@router.get("/conversations")
async def list_conversations() -> dict:
    """历史会话列表"""
    import json
    from pathlib import Path

    log_dir = Path("logs")
    if not log_dir.exists():
        return {"conversations": []}

    conversations = []
    for f in sorted(log_dir.glob("*.jsonl"), reverse=True)[:50]:
        try:
            first_line = f.read_text(encoding="utf-8").split("\n", 1)[0]
            event = json.loads(first_line)
            conversations.append(
                {
                    "id": f.stem,
                    "file": f.name,
                    "started_at": event.get("ts", ""),
                    "first_message": event.get("content", "")[:100],
                }
            )
        except Exception:
            continue

    return {"conversations": conversations}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict:
    """单个会话的完整消息"""
    import json
    from pathlib import Path

    log_file = Path("logs") / f"{conversation_id}.jsonl"
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="会话不存在")

    events = []
    for line in log_file.read_text(encoding="utf-8").strip().split("\n"):
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return {"id": conversation_id, "events": events}
