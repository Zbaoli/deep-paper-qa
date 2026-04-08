"""SSE 事件类型定义和构造函数"""

import json
from typing import Any

from sse_starlette.sse import ServerSentEvent


def _event(event_type: str, data: dict[str, Any]) -> ServerSentEvent:
    """构造 SSE 事件"""
    return ServerSentEvent(event=event_type, data=json.dumps(data, ensure_ascii=False))


def sse_route(category: str, label: str) -> ServerSentEvent:
    """路由分类事件"""
    return _event("route", {"category": category, "label": label})


def sse_tool_start(tool: str, input_data: Any, run_id: str) -> ServerSentEvent:
    """工具调用开始事件"""
    return _event("tool_start", {"tool": tool, "input": input_data, "run_id": run_id})


def sse_tool_end(tool: str, output: str, duration_ms: int, run_id: str) -> ServerSentEvent:
    """工具调用结束事件"""
    return _event(
        "tool_end",
        {"tool": tool, "output": output, "duration_ms": duration_ms, "run_id": run_id},
    )


def sse_token(content: str) -> ServerSentEvent:
    """LLM 流式 token 事件"""
    return _event("token", {"content": content})


def sse_chart(option: dict[str, Any]) -> ServerSentEvent:
    """图表事件（ECharts option）"""
    return _event("chart", {"type": "echarts", "option": option})


def sse_chart_plotly(figure: dict[str, Any]) -> ServerSentEvent:
    """图表事件（Plotly figure dict）"""
    return _event("chart", {"type": "plotly", "figure": figure})


def sse_ask_user(question: str, summary: str) -> ServerSentEvent:
    """ask_user 交互事件"""
    return _event("ask_user", {"question": question, "summary": summary})


def sse_done(total_ms: int, tool_calls: int) -> ServerSentEvent:
    """完成事件"""
    return _event("done", {"total_ms": total_ms, "tool_calls": tool_calls})


def sse_error(message: str) -> ServerSentEvent:
    """错误事件"""
    return _event("error", {"message": message})
