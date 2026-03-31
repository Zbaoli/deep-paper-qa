"""评测脚本：批量运行 Agent 并评估结果"""

import asyncio
import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage
from loguru import logger

from deep_paper_qa.agent import build_agent


async def run_eval() -> None:
    """运行评测"""
    questions_file = Path(__file__).parent / "questions.jsonl"
    questions = [json.loads(line) for line in questions_file.read_text().strip().split("\n")]

    agent, trimmer, checkpointer = build_agent()

    results: list[dict] = []
    correct_tool_routing = 0
    total = len(questions)

    for q in questions:
        qid = q["id"]
        question = q["question"]
        q_type = q["type"]
        logger.info("评测 #{}: [{}] {}", qid, q_type, question)

        config = {
            "configurable": {"thread_id": f"eval_{qid}"},
            "recursion_limit": 10,
        }

        tools_called: list[str] = []
        final_answer = ""

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
                elif kind == "on_chat_model_end":
                    chunk = event.get("data", {}).get("output", None)
                    if chunk and hasattr(chunk, "content"):
                        final_answer = chunk.content

        except Exception as e:
            logger.error("评测 #{} 执行失败: {}", qid, e)
            final_answer = f"ERROR: {e}"

        # 评估工具路由正确性
        tool_correct = False
        if q_type == "sql":
            tool_correct = "execute_sql" in tools_called
        elif q_type == "content":
            tool_correct = "vector_search" in tools_called
        elif q_type == "mixed":
            expected = set(q.get("expected_tools", []))
            tool_correct = expected.issubset(set(tools_called))

        if tool_correct:
            correct_tool_routing += 1

        result = {
            "id": qid,
            "type": q_type,
            "question": question,
            "tools_called": tools_called,
            "tool_routing_correct": tool_correct,
            "answer_length": len(final_answer),
            "answer_preview": final_answer[:200],
        }
        results.append(result)
        logger.info("  工具调用: {} | 路由正确: {}", tools_called, tool_correct)

    # 汇总统计
    logger.info("=" * 60)
    logger.info("评测完成: {}/{} 工具路由正确 ({:.1f}%)", correct_tool_routing, total, correct_tool_routing / total * 100)

    by_type: dict[str, list[bool]] = {}
    for r in results:
        by_type.setdefault(r["type"], []).append(r["tool_routing_correct"])

    for t, corrections in by_type.items():
        correct = sum(corrections)
        logger.info("  {}: {}/{} ({:.1f}%)", t, correct, len(corrections), correct / len(corrections) * 100)

    # 保存结果
    output_file = Path(__file__).parent / "eval_results.json"
    output_file.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    logger.info("结果已保存到: {}", output_file)


if __name__ == "__main__":
    asyncio.run(run_eval())
