"""聊天 API 路由：SSE 事件流 + ask_user 回复"""

import re
import time

from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from loguru import logger
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from deep_paper_qa.agent import CATEGORY_LABELS, build_graph
from deep_paper_qa.conversation_logger import ConversationLogger
from deep_paper_qa.sse_events import (
    sse_ask_user,
    sse_chart_plotly,
    sse_done,
    sse_error,
    sse_route,
    sse_token,
    sse_tool_end,
    sse_tool_start,
)
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
        graph = _get_graph()
        config = {
            "configurable": {"thread_id": req.thread_id},
            "recursion_limit": 50,
        }

        logger.info("API chat | thread={} | message={}", req.thread_id, req.message[:200])
        _conv_logger.log_user_message(req.thread_id, req.message)

        msg_start = time.monotonic()
        tool_call_count = 0
        tools_used: list[str] = []
        tool_timings: dict[str, tuple[str, float]] = {}
        router_shown = False

        try:
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content=req.message)]},
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")
                name = event.get("name", "")

                # 路由分类
                if kind == "on_chain_end" and name == "router" and not router_shown:
                    try:
                        output = event.get("data", {}).get("output", {})
                        cat = output.get("category", "")
                        if cat:
                            label = CATEGORY_LABELS.get(cat, cat)
                            yield sse_route(cat, label)
                            router_shown = True
                    except Exception:
                        pass

                # 工具开始
                elif kind == "on_tool_start":
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
                        yield sse_ask_user(question, summary)
                    else:
                        yield sse_tool_start(name, tool_input, run_id)

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
                        yield sse_tool_end(
                            tool_name,
                            output_str[:500] if len(output_str) > 500 else output_str,
                            duration_ms,
                            run_id,
                        )

                # LLM 流式 token
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", None)
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield sse_token(chunk.content)

            # 非流式 pipeline：从 state 获取最终消息
            try:
                state = _get_graph().get_state(config)
                msgs = state.values.get("messages", [])
                for m in reversed(msgs):
                    if isinstance(m, AIMessage) and m.content:
                        content = m.content
                        # 提取 plotly 图表转为 chart 事件
                        plotly_match = re.search(r"<!--plotly:(.*?)-->", content, re.DOTALL)
                        if plotly_match:
                            import json as json_mod  # noqa: F401
                            import plotly.io as pio

                            chart_json = plotly_match.group(1)
                            content = re.sub(r"<!--plotly:.*?-->\n*", "", content, flags=re.DOTALL)
                            try:
                                fig = pio.from_json(chart_json)
                                yield sse_token(content)
                                yield sse_chart_plotly(fig.to_dict())
                            except Exception:
                                yield sse_token(content)
                        break
            except Exception as e:
                logger.warning("获取最终状态失败: {}", e)

            total_ms = int((time.monotonic() - msg_start) * 1000)
            _conv_logger.log_agent_reply(req.thread_id, "", total_ms, tool_call_count, tools_used)
            yield sse_done(total_ms, tool_call_count)

        except Exception as e:
            logger.error("API chat 异常 | thread={} | error={}", req.thread_id, e)
            yield sse_error(str(e))

    return EventSourceResponse(event_stream())


@router.post("/chat/{thread_id}/reply")
async def reply(thread_id: str, req: ReplyRequest) -> dict[str, str]:
    """提交 ask_user 回复"""
    pending = get_pending_question(thread_id)
    if not pending:
        raise HTTPException(status_code=404, detail="没有等待中的问题")

    submit_reply(thread_id, req.reply)
    return {"status": "ok"}
