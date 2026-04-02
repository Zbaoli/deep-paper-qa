"""评测脚本：并发运行 Agent 并评估结果"""

import asyncio
import json
from pathlib import Path

from langchain_core.messages import HumanMessage
from loguru import logger

from deep_paper_qa.agent import build_agent

# 并发数
MAX_CONCURRENCY = 10


async def eval_one(agent, q: dict) -> dict:
    """评测单个问题，返回结果字典"""
    qid = q["id"]
    question = q["question"]
    q_type = q["type"]
    logger.info("评测 #{}: [{}] {}", qid, q_type, question)

    config = {
        "configurable": {"thread_id": f"eval_{qid}"},
        "recursion_limit": 30,
    }

    tools_called: list[str] = []
    tool_details: list[dict] = []
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

    # 评估工具路由正确性
    tool_correct = False
    called_set = set(tools_called)
    if q_type == "sql":
        tool_correct = "execute_sql" in called_set
    elif q_type == "content":
        tool_correct = bool(called_set & {"vector_search", "search_abstracts"})
    elif q_type == "mixed":
        expected = set(q.get("expected_tools", []))
        content_tools = {"vector_search", "search_abstracts"}
        has_sql = "execute_sql" in called_set if "execute_sql" in expected else True
        has_content = bool(called_set & content_tools) if expected & content_tools else True
        tool_correct = has_sql and has_content

    logger.info("  #{} 工具调用: {} | 路由正确: {}", qid, tools_called, tool_correct)

    return {
        "id": qid,
        "type": q_type,
        "question": question,
        "tools_called": tools_called,
        "tool_details": tool_details,
        "tool_call_count": len(tools_called),
        "tool_routing_correct": tool_correct,
        "answer_length": len(final_answer),
        "answer_preview": final_answer[:200],
    }


async def run_eval() -> None:
    """并发运行评测（信号量控制并发数）"""
    questions_file = Path(__file__).parent / "questions.jsonl"
    questions = [json.loads(line) for line in questions_file.read_text().strip().split("\n")]
    total = len(questions)

    agent, checkpointer = build_agent()
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def bounded_eval(q: dict) -> dict:
        async with semaphore:
            return await eval_one(agent, q)

    # 并发执行所有题目
    logger.info("开始评测: {} 题, 并发数 {}", total, MAX_CONCURRENCY)
    results = await asyncio.gather(*(bounded_eval(q) for q in questions))

    # 按 id 排序
    results = sorted(results, key=lambda r: r["id"])

    # 汇总统计
    correct_tool_routing = sum(1 for r in results if r["tool_routing_correct"])
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
