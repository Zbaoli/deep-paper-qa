"""评测脚本：批量运行 Agent 并评估结果

research 类型题目需要 mock chainlit 的 AskUserMessage，
必须在 import agent 之前注入 sys.modules["chainlit"]。
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import HumanMessage
from loguru import logger

# research 模式下 ask_user 的自动回复序列
_ASK_USER_AUTO_REPLIES = [
    "继续",  # 确认研究计划
    "继续",  # 第 1 个子问题完成后继续
    "继续",  # 第 2 个子问题完成后继续
    "总结",  # 第 3 个子问题完成后要求总结
]

_ask_user_call_count = 0


def _install_chainlit_mock() -> None:
    """注入 chainlit mock 到 sys.modules，AskUserMessage.send() 返回自动回复"""
    global _ask_user_call_count
    _ask_user_call_count = 0

    mock_cl = MagicMock()

    def _make_ask_user_message(content: str, timeout: int = 300) -> MagicMock:
        """每次 AskUserMessage() 被调用时，返回一个 mock 对象，其 send() 返回自动回复"""
        global _ask_user_call_count
        idx = min(_ask_user_call_count, len(_ASK_USER_AUTO_REPLIES) - 1)
        reply_text = _ASK_USER_AUTO_REPLIES[idx]
        _ask_user_call_count += 1

        mock_response = MagicMock()
        mock_response.output = reply_text

        msg = MagicMock()
        msg.send = AsyncMock(return_value=mock_response)

        logger.info(
            "ask_user [eval mock] | 第{}次调用 | content_len={} | 自动回复: {}",
            _ask_user_call_count, len(content), reply_text,
        )
        return msg

    mock_cl.AskUserMessage = _make_ask_user_message
    sys.modules["chainlit"] = mock_cl  # type: ignore[assignment]


# 在 import agent 之前注入 mock — 这样 ask_user.py 中的 `import chainlit as cl` 拿到的是 mock
_install_chainlit_mock()

from deep_paper_qa.agent import build_agent  # noqa: E402


async def eval_one(agent, q: dict) -> dict:
    """评测单个问题，返回结果字典"""
    qid = q["id"]
    question = q["question"]
    q_type = q["type"]
    is_research = q_type == "research"

    logger.info("评测 #{}: [{}] {}", qid, q_type, question)

    # research 题目重置 ask_user 自动回复计数器
    if is_research:
        global _ask_user_call_count
        _ask_user_call_count = 0

    config = {
        "configurable": {"thread_id": f"eval_{qid}"},
        "recursion_limit": 50 if is_research else 30,
    }

    tools_called: list[str] = []
    tool_details: list[dict] = []
    final_answer = ""
    start_time = time.monotonic()

    try:
        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=question)]},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")
            name = event.get("name", "")

            if kind == "on_tool_start":
                tools_called.append(name)
                tool_input = event.get("data", {}).get("input", {})
                tool_details.append({
                    "name": name,
                    "input": str(tool_input)[:500],
                })
            elif kind == "on_tool_end":
                output = event.get("data", {}).get("output", "")
                if hasattr(output, "content"):
                    output = output.content
                if tool_details:
                    tool_details[-1]["output"] = str(output)[:500]
            elif kind == "on_chat_model_end":
                chunk = event.get("data", {}).get("output", None)
                if chunk and hasattr(chunk, "content"):
                    final_answer = chunk.content

    except Exception as e:
        logger.error("评测 #{} 执行失败: {}", qid, e)
        final_answer = f"ERROR: {e}"

    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    # 评估工具路由正确性
    tool_correct = _check_tool_routing(q_type, q, tools_called)

    # research 类型额外评估
    research_metrics = {}
    if is_research:
        research_metrics = _eval_research_quality(tools_called, final_answer)

    logger.info(
        "  #{} 工具调用: {} | 路由正确: {} | 耗时: {}ms",
        qid, tools_called, tool_correct, elapsed_ms,
    )

    return {
        "id": qid,
        "type": q_type,
        "question": question,
        "tools_called": tools_called,
        "tool_details": tool_details,
        "tool_call_count": len(tools_called),
        "tool_routing_correct": tool_correct,
        "answer_length": len(final_answer),
        "answer_preview": final_answer[:500],
        "elapsed_ms": elapsed_ms,
        **research_metrics,
    }


def _check_tool_routing(q_type: str, q: dict, tools_called: list[str]) -> bool:
    """检查工具路由正确性"""
    called_set = set(tools_called)

    if q_type == "sql":
        return "execute_sql" in called_set
    elif q_type == "content":
        return bool(called_set & {"vector_search", "search_abstracts"})
    elif q_type == "mixed":
        expected = set(q.get("expected_tools", []))
        content_tools = {"vector_search", "search_abstracts"}
        has_sql = "execute_sql" in called_set if "execute_sql" in expected else True
        has_content = bool(called_set & content_tools) if expected & content_tools else True
        return has_sql and has_content
    elif q_type == "research":
        # research 类型：必须调用 ask_user + 至少一个检索工具
        has_ask_user = "ask_user" in called_set
        has_search = bool(called_set & {"execute_sql", "vector_search", "search_abstracts"})
        return has_ask_user and has_search

    return False


def _eval_research_quality(tools_called: list[str], answer: str) -> dict:
    """评估 research 类型的回答质量"""
    ask_user_count = tools_called.count("ask_user")
    search_tools = [t for t in tools_called if t != "ask_user"]
    unique_search_tools = set(search_tools)

    return {
        "research_ask_user_count": ask_user_count,
        "research_search_tool_count": len(search_tools),
        "research_unique_tools": list(unique_search_tools),
        "research_has_plan": ask_user_count >= 1,  # 至少调用 1 次 ask_user（展示计划）
        "research_has_multi_round": len(search_tools) >= 3,  # 至少 3 次检索
        "research_has_citations": bool(
            any(marker in answer for marker in ["(", "2020", "2021", "2022", "2023", "2024", "2025"])
        ),
    }


async def run_eval() -> None:
    """运行评测"""
    questions_file = Path(__file__).parent / "questions.jsonl"
    all_questions = [json.loads(line) for line in questions_file.read_text().strip().split("\n")]

    # 支持 --type 参数过滤题型
    filter_type = None
    if len(sys.argv) > 1:
        filter_type = sys.argv[1]
        logger.info("过滤题型: {}", filter_type)

    questions = [q for q in all_questions if filter_type is None or q["type"] == filter_type]
    total = len(questions)

    agent, checkpointer = build_agent()
    logger.info("chainlit 已 mock，ask_user 将自动回复: {}", _ASK_USER_AUTO_REPLIES)

    # 逐题执行（research 题目不适合高并发，因为 ask_user mock 有状态）
    results: list[dict] = []
    for q in questions:
        result = await eval_one(agent, q)
        results.append(result)

    # 按 id 排序
    results = sorted(results, key=lambda r: r["id"])

    # 汇总统计
    correct_tool_routing = sum(1 for r in results if r["tool_routing_correct"])
    logger.info("=" * 60)
    logger.info(
        "评测完成: {}/{} 工具路由正确 ({:.1f}%)",
        correct_tool_routing, total, correct_tool_routing / total * 100,
    )

    by_type: dict[str, list[bool]] = {}
    for r in results:
        by_type.setdefault(r["type"], []).append(r["tool_routing_correct"])

    for t, corrections in by_type.items():
        correct = sum(corrections)
        logger.info(
            "  {}: {}/{} ({:.1f}%)", t, correct, len(corrections),
            correct / len(corrections) * 100,
        )

    # 保存结果
    output_file = Path(__file__).parent / "eval_results.json"
    output_file.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    logger.info("结果已保存到: {}", output_file)


if __name__ == "__main__":
    asyncio.run(run_eval())
