"""SSE 事件构造器测试"""

import json

from deep_paper_qa.sse_events import sse


class TestSseBuilder:
    """sse() 通用构造器测试"""

    def test_event_name_set(self) -> None:
        event = sse("token", {"content": "hi"})
        assert event.event == "token"

    def test_data_is_json(self) -> None:
        event = sse("tool_start", {"tool": "execute_sql", "run_id": "abc"})
        data = json.loads(event.data)
        assert data["tool"] == "execute_sql"
        assert data["run_id"] == "abc"

    def test_none_data_becomes_empty_object(self) -> None:
        event = sse("done")
        data = json.loads(event.data)
        assert data == {}

    def test_ensure_ascii_false_for_chinese(self) -> None:
        event = sse("token", {"content": "论文"})
        # data 字符串应保留中文，不应是 \u escaped
        assert "论文" in event.data
