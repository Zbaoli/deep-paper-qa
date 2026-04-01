"""结构化对话事件记录器，写入 JSONL 文件用于评测分析"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger


class ConversationLogger:
    """将对话事件以 JSONL 格式写入文件。

    每个 thread_id 对应一个独立的 JSONL 文件：logs/{thread_id}.jsonl。
    写入失败不影响主流程，仅 logger.warning 记录。
    """

    def __init__(self, log_dir: str = "logs") -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, thread_id: str) -> Path:
        """根据 thread_id 获取对应的 JSONL 文件路径"""
        return self._log_dir / f"{thread_id}.jsonl"

    def _write_event(self, thread_id: str, event: dict[str, Any]) -> None:
        """写入单条事件到对应 thread 的 JSONL 文件"""
        event["ts"] = datetime.now(timezone.utc).isoformat()
        try:
            line = json.dumps(event, ensure_ascii=False, default=str)
            with open(self._get_file_path(thread_id), "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
        except Exception as e:
            logger.warning("JSONL 写入失败: {}", e)

    def log_user_message(self, thread_id: str, content: str) -> None:
        """记录用户消息事件"""
        self._write_event(thread_id, {
            "thread_id": thread_id,
            "event": "user_message",
            "content": content,
        })

    def log_tool_start(self, thread_id: str, tool: str, input_data: dict) -> None:
        """记录工具调用开始事件"""
        self._write_event(thread_id, {
            "thread_id": thread_id,
            "event": "tool_start",
            "tool": tool,
            "input": input_data,
        })

    def log_tool_end(
        self, thread_id: str, tool: str, duration_ms: int, output: str
    ) -> None:
        """记录工具调用结束事件"""
        self._write_event(thread_id, {
            "thread_id": thread_id,
            "event": "tool_end",
            "tool": tool,
            "duration_ms": duration_ms,
            "output": output,
        })

    def log_agent_reply(
        self,
        thread_id: str,
        content: str,
        total_ms: int,
        tool_calls: int,
        tools_used: list[str],
    ) -> None:
        """记录 Agent 最终回答事件"""
        self._write_event(thread_id, {
            "thread_id": thread_id,
            "event": "agent_reply",
            "content": content,
            "total_ms": total_ms,
            "tool_calls": tool_calls,
            "tools_used": tools_used,
        })
