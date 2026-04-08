"""SSE 事件转换测试"""

import json

from deep_paper_qa.sse_events import (
    sse_ask_user,
    sse_chart,
    sse_done,
    sse_error,
    sse_route,
    sse_token,
    sse_tool_end,
    sse_tool_start,
)


class TestSseEventBuilders:
    """SSE 事件构造函数测试"""

    def test_route_event(self) -> None:
        event = sse_route("general", "普通问答")
        assert event.event == "route"
        data = json.loads(event.data)
        assert data["category"] == "general"
        assert data["label"] == "普通问答"

    def test_tool_start_event(self) -> None:
        event = sse_tool_start("execute_sql", {"sql": "SELECT 1"}, "run-123")
        assert event.event == "tool_start"
        data = json.loads(event.data)
        assert data["tool"] == "execute_sql"
        assert data["input"]["sql"] == "SELECT 1"
        assert data["run_id"] == "run-123"

    def test_tool_end_event(self) -> None:
        event = sse_tool_end("execute_sql", "result", 120, "run-123")
        assert event.event == "tool_end"
        data = json.loads(event.data)
        assert data["tool"] == "execute_sql"
        assert data["output"] == "result"
        assert data["duration_ms"] == 120

    def test_token_event(self) -> None:
        event = sse_token("根据")
        assert event.event == "token"
        data = json.loads(event.data)
        assert data["content"] == "根据"

    def test_chart_event(self) -> None:
        option = {"xAxis": {"data": ["2020", "2021"]}}
        event = sse_chart(option)
        assert event.event == "chart"
        data = json.loads(event.data)
        assert data["type"] == "echarts"
        assert data["option"]["xAxis"]["data"][0] == "2020"

    def test_ask_user_event(self) -> None:
        event = sse_ask_user("请确认", "摘要内容")
        assert event.event == "ask_user"
        data = json.loads(event.data)
        assert data["question"] == "请确认"
        assert data["summary"] == "摘要内容"

    def test_done_event(self) -> None:
        event = sse_done(3200, 2)
        assert event.event == "done"
        data = json.loads(event.data)
        assert data["total_ms"] == 3200
        assert data["tool_calls"] == 2

    def test_error_event(self) -> None:
        event = sse_error("处理失败")
        assert event.event == "error"
        data = json.loads(event.data)
        assert data["message"] == "处理失败"
