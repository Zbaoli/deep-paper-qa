"""ConversationLogger 单元测试"""

import json
from pathlib import Path

import pytest

from deep_paper_qa.conversation_logger import ConversationLogger


@pytest.fixture()
def logger_instance(tmp_path: Path) -> ConversationLogger:
    """使用临时目录的 ConversationLogger 实例"""
    return ConversationLogger(log_dir=str(tmp_path))


def _find_jsonl(directory: Path) -> list[Path]:
    """查找目录下所有 .jsonl 文件"""
    return sorted(directory.glob("*.jsonl"))


def _read_events(path: Path) -> list[dict]:
    """读取 JSONL 文件的所有事件"""
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    return [json.loads(line) for line in lines if line.strip()]


class TestLogUserMessage:
    def test_writes_user_message_event(
        self, logger_instance: ConversationLogger, tmp_path: Path
    ) -> None:
        logger_instance.log_user_message("thread-1", "ACL 2025 多少篇论文")

        files = _find_jsonl(tmp_path)
        assert len(files) == 1
        events = _read_events(files[0])
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "user_message"
        assert e["thread_id"] == "thread-1"
        assert e["content"] == "ACL 2025 多少篇论文"
        assert "ts" in e


class TestLogToolStart:
    def test_writes_tool_start_event(
        self, logger_instance: ConversationLogger, tmp_path: Path
    ) -> None:
        logger_instance.log_tool_start(
            "thread-1", "execute_sql", {"sql": "SELECT COUNT(*) FROM papers"}
        )

        files = _find_jsonl(tmp_path)
        assert len(files) == 1
        events = _read_events(files[0])
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "tool_start"
        assert e["tool"] == "execute_sql"
        assert e["input"] == {"sql": "SELECT COUNT(*) FROM papers"}


class TestLogToolEnd:
    def test_writes_tool_end_event(
        self, logger_instance: ConversationLogger, tmp_path: Path
    ) -> None:
        logger_instance.log_tool_end("thread-1", "execute_sql", 150, "42")

        files = _find_jsonl(tmp_path)
        assert len(files) == 1
        events = _read_events(files[0])
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "tool_end"
        assert e["tool"] == "execute_sql"
        assert e["duration_ms"] == 150
        assert e["output"] == "42"


class TestLogAgentReply:
    def test_writes_agent_reply_event(
        self, logger_instance: ConversationLogger, tmp_path: Path
    ) -> None:
        logger_instance.log_agent_reply("thread-1", "共 42 篇", 3200, 1, ["execute_sql"])

        files = _find_jsonl(tmp_path)
        assert len(files) == 1
        events = _read_events(files[0])
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "agent_reply"
        assert e["content"] == "共 42 篇"
        assert e["total_ms"] == 3200
        assert e["tool_calls"] == 1
        assert e["tools_used"] == ["execute_sql"]


class TestMultipleEvents:
    def test_appends_to_same_thread_file(
        self, logger_instance: ConversationLogger, tmp_path: Path
    ) -> None:
        logger_instance.log_user_message("t1", "问题1")
        logger_instance.log_tool_start("t1", "execute_sql", {"sql": "SELECT 1"})
        logger_instance.log_tool_end("t1", "execute_sql", 100, "1")
        logger_instance.log_agent_reply("t1", "回答", 500, 1, ["execute_sql"])

        files = _find_jsonl(tmp_path)
        assert len(files) == 1
        events = _read_events(files[0])
        assert len(events) == 4
        assert [e["event"] for e in events] == [
            "user_message",
            "tool_start",
            "tool_end",
            "agent_reply",
        ]


class TestFileNaming:
    def test_file_named_by_timestamp(
        self, logger_instance: ConversationLogger, tmp_path: Path
    ) -> None:
        """文件名应为时间戳格式 YYYY-MM-DD_HH-MM-SS.jsonl"""
        logger_instance.log_user_message("t1", "test")

        files = _find_jsonl(tmp_path)
        assert len(files) == 1
        # 验证文件名格式：YYYY-MM-DD_HH-MM-SS.jsonl
        import re

        assert re.match(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.jsonl", files[0].name)

    def test_different_threads_write_to_different_files(self, tmp_path: Path) -> None:
        """不同 thread_id 写入不同文件"""
        import time

        cl = ConversationLogger(log_dir=str(tmp_path))
        cl.log_user_message("thread-a", "问题A")
        time.sleep(1.1)  # 确保时间戳不同
        cl.log_user_message("thread-b", "问题B")

        files = _find_jsonl(tmp_path)
        assert len(files) == 2
        events_a = _read_events(files[0])
        events_b = _read_events(files[1])
        assert events_a[0]["content"] == "问题A"
        assert events_b[0]["content"] == "问题B"


class TestDirectoryCreation:
    def test_creates_log_dir_if_not_exists(self, tmp_path: Path) -> None:
        new_dir = tmp_path / "subdir" / "logs"
        cl = ConversationLogger(log_dir=str(new_dir))
        cl.log_user_message("t1", "test")

        files = _find_jsonl(new_dir)
        assert len(files) == 1
