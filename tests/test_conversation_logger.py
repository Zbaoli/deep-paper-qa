"""ConversationLogger 单元测试"""

import json
from pathlib import Path

import pytest

from deep_paper_qa.conversation_logger import ConversationLogger


@pytest.fixture()
def logger_instance(tmp_path: Path) -> ConversationLogger:
    """使用临时目录的 ConversationLogger 实例"""
    return ConversationLogger(log_dir=str(tmp_path))


@pytest.fixture()
def events_file(tmp_path: Path) -> Path:
    """JSONL 文件路径"""
    return tmp_path / "events.jsonl"


def _read_events(path: Path) -> list[dict]:
    """读取 JSONL 文件的所有事件"""
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    return [json.loads(line) for line in lines if line.strip()]


class TestLogUserMessage:
    def test_writes_user_message_event(
        self, logger_instance: ConversationLogger, events_file: Path
    ) -> None:
        logger_instance.log_user_message("thread-1", "ACL 2025 多少篇论文")

        events = _read_events(events_file)
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "user_message"
        assert e["thread_id"] == "thread-1"
        assert e["content"] == "ACL 2025 多少篇论文"
        assert "ts" in e


class TestLogToolStart:
    def test_writes_tool_start_event(
        self, logger_instance: ConversationLogger, events_file: Path
    ) -> None:
        logger_instance.log_tool_start(
            "thread-1", "execute_sql", {"sql": "SELECT COUNT(*) FROM papers"}
        )

        events = _read_events(events_file)
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "tool_start"
        assert e["tool"] == "execute_sql"
        assert e["input"] == {"sql": "SELECT COUNT(*) FROM papers"}


class TestLogToolEnd:
    def test_writes_tool_end_event(
        self, logger_instance: ConversationLogger, events_file: Path
    ) -> None:
        logger_instance.log_tool_end("thread-1", "execute_sql", 150, "42")

        events = _read_events(events_file)
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "tool_end"
        assert e["tool"] == "execute_sql"
        assert e["duration_ms"] == 150
        assert e["output"] == "42"


class TestLogAgentReply:
    def test_writes_agent_reply_event(
        self, logger_instance: ConversationLogger, events_file: Path
    ) -> None:
        logger_instance.log_agent_reply(
            "thread-1", "共 42 篇", 3200, 1, ["execute_sql"]
        )

        events = _read_events(events_file)
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "agent_reply"
        assert e["content"] == "共 42 篇"
        assert e["total_ms"] == 3200
        assert e["tool_calls"] == 1
        assert e["tools_used"] == ["execute_sql"]


class TestMultipleEvents:
    def test_appends_to_same_file(
        self, logger_instance: ConversationLogger, events_file: Path
    ) -> None:
        logger_instance.log_user_message("t1", "问题1")
        logger_instance.log_tool_start("t1", "execute_sql", {"sql": "SELECT 1"})
        logger_instance.log_tool_end("t1", "execute_sql", 100, "1")
        logger_instance.log_agent_reply("t1", "回答", 500, 1, ["execute_sql"])

        events = _read_events(events_file)
        assert len(events) == 4
        assert [e["event"] for e in events] == [
            "user_message", "tool_start", "tool_end", "agent_reply"
        ]


class TestDirectoryCreation:
    def test_creates_log_dir_if_not_exists(self, tmp_path: Path) -> None:
        new_dir = tmp_path / "subdir" / "logs"
        cl = ConversationLogger(log_dir=str(new_dir))
        cl.log_user_message("t1", "test")

        assert (new_dir / "events.jsonl").exists()
