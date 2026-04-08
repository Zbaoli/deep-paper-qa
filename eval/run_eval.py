"""评测脚本：并发运行 Agent 并评估工具路由 + 回答质量（LLM-as-Judge）"""

import asyncio
import json
import statistics
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage
from loguru import logger

from deep_paper_qa.agent import build_agent
from eval.judge import judge_answer

# 并发数
MAX_CONCURRENCY = 10


async def eval_one(agent, q: dict) -> dict:
    """评测单个问题，返回结果字典（含完整回答和工具输出）"""
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
    # 完整工具输出（传给 judge）
    tool_outputs_full: list[str] = []
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
                tool_details.append(
                    {
                        "name": name,
                        "input": str(tool_input),
                    }
                )
            elif kind == "on_tool_end":
                output = event.get("data", {}).get("output", "")
                if hasattr(output, "content"):
                    output = output.content
                output_str = str(output)
                # 完整输出给 judge
                tool_outputs_full.append(f"[{tool_details[-1]['name']}] {output_str}")
                # 截断版存入 eval_results.json
                if tool_details:
                    tool_details[-1]["output"] = output_str
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
    # Agent 直接回答（0 次调用）且回答合理也视为正确
    no_tool_but_reasonable = (
        len(called_set) == 0 and not final_answer.startswith("ERROR:") and len(final_answer) > 20
    )
    if q_type == "sql":
        tool_correct = "execute_sql" in called_set or no_tool_but_reasonable
    elif q_type == "content":
        tool_correct = (
            bool(called_set & {"vector_search", "search_abstracts"}) or no_tool_but_reasonable
        )
    elif q_type == "mixed":
        expected = set(q.get("expected_tools", []))
        content_tools = {"vector_search", "search_abstracts"}
        # search_abstracts/vector_search 带非空 where 参数也视为完成了筛选意图
        content_with_where = any(
            td["name"] in content_tools
            and "'where':" in td["input"]
            and "'where': ''" not in td["input"]
            and "'where': \"\"" not in td["input"]
            for td in tool_details
        )
        has_sql = (
            ("execute_sql" in called_set or content_with_where)
            if "execute_sql" in expected
            else True
        )
        has_content = bool(called_set & content_tools) if expected & content_tools else True
        tool_correct = has_sql and has_content
    elif q_type == "trend":
        # 趋势分析需要同时用 SQL 统计和内容检索
        tool_correct = "execute_sql" in called_set and bool(
            called_set & {"search_abstracts", "vector_search"}
        )
    elif q_type == "research":
        # 深度研究需要多次工具调用
        tool_correct = len(tools_called) >= 3
    elif q_type == "reject":
        # 拒答不应调用任何工具
        tool_correct = len(called_set) == 0

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
        # 完整数据（用于 judge，不写入最终 JSON）
        "_full_answer": final_answer,
        "_tool_outputs_full": "\n\n".join(tool_outputs_full),
    }


async def judge_results(results: list[dict], semaphore: asyncio.Semaphore) -> None:
    """批量对所有评测结果进行 LLM-as-Judge 评分"""
    logger.info("开始 LLM-as-Judge 质量评分: {} 题", len(results))

    async def judge_one(r: dict) -> None:
        async with semaphore:
            # 生成工具调用摘要供 Judge 评估效率
            call_summary = "\n".join(
                f"{i + 1}. {td['name']}({td['input'][:150]})"
                for i, td in enumerate(r["tool_details"])
            )
            scores = await judge_answer(
                question=r["question"],
                question_type=r["type"],
                answer=r["_full_answer"],
                tool_outputs=r["_tool_outputs_full"],
                tool_call_count=r["tool_call_count"],
                tool_call_summary=call_summary,
            )
            r["quality_scores"] = scores

    await asyncio.gather(*(judge_one(r) for r in results))

    scored = sum(1 for r in results if r.get("quality_scores"))
    logger.info("质量评分完成: {}/{} 题成功", scored, len(results))


def _generate_report(results: list[dict], total: int) -> str:
    """生成评测报告（Markdown 格式）"""
    now = datetime.now()
    lines: list[str] = []
    lines.append("# Agent 评测报告")
    lines.append(f"\n**时间**: {now.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**题目数**: {total}")

    # --- 路由统计 ---
    correct_routing = sum(1 for r in results if r["tool_routing_correct"])
    lines.append(
        f"**工具路由正确率**: {correct_routing}/{total} ({correct_routing / total * 100:.1f}%)"
    )

    completed = sum(1 for r in results if not r.get("_full_answer", "").startswith("ERROR:"))
    lines.append(f"**完成率**: {completed}/{total} ({completed / total * 100:.1f}%)")

    avg_tools = statistics.mean(r["tool_call_count"] for r in results) if results else 0
    lines.append(f"**平均工具调用**: {avg_tools:.1f} 次/题")

    # --- 质量评分汇总 ---
    scored_results = [r for r in results if r.get("quality_scores")]
    if scored_results:
        lines.append("\n---\n")
        lines.append("## 回答质量评分（LLM-as-Judge）")
        lines.append(f"\n**评分成功**: {len(scored_results)}/{total} 题\n")

        # 总体平均分
        all_overalls = [r["quality_scores"]["overall"] for r in scored_results]
        avg_overall = statistics.mean(all_overalls)
        std_overall = statistics.stdev(all_overalls) if len(all_overalls) > 1 else 0
        lines.append(f"**总体平均分**: {avg_overall:.2f} / 5.00（标准差: {std_overall:.2f}）\n")

        # 按维度汇总
        dims = ["accuracy", "completeness", "citation", "clarity", "efficiency"]
        lines.append("| 维度 | 平均分 | 最低分 | 最高分 |")
        lines.append("|------|--------|--------|--------|")
        for dim in dims:
            scores = [r["quality_scores"][dim]["score"] for r in scored_results]
            lines.append(
                f"| {dim} | {statistics.mean(scores):.2f} | {min(scores)} | {max(scores)} |"
            )

        # 按题型分组
        lines.append("\n### 按题型质量分布\n")
        lines.append(
            "| 题型 | 题数 | overall | accuracy | completeness | citation | clarity | efficiency |"
        )
        lines.append(
            "|------|------|---------|----------|--------------|----------|---------|------------|"
        )
        by_type: dict[str, list[dict]] = {}
        for r in scored_results:
            by_type.setdefault(r["type"], []).append(r)
        for t in ["sql", "content", "mixed", "trend", "research", "reject"]:
            type_results = by_type.get(t, [])
            if not type_results:
                continue
            o = statistics.mean(r["quality_scores"]["overall"] for r in type_results)
            a = statistics.mean(r["quality_scores"]["accuracy"]["score"] for r in type_results)
            comp = statistics.mean(
                r["quality_scores"]["completeness"]["score"] for r in type_results
            )
            c = statistics.mean(r["quality_scores"]["citation"]["score"] for r in type_results)
            cl = statistics.mean(r["quality_scores"]["clarity"]["score"] for r in type_results)
            ef = statistics.mean(r["quality_scores"]["efficiency"]["score"] for r in type_results)
            lines.append(
                f"| {t} | {len(type_results)} | {o:.2f} | {a:.2f} | {comp:.2f} | {c:.2f} | {cl:.2f} | {ef:.2f} |"
            )

        # 低分题（overall < 3）
        low_score = [r for r in scored_results if r["quality_scores"]["overall"] < 3]
        if low_score:
            lines.append(f"\n### 低分题（overall < 3，共 {len(low_score)} 题）\n")
            lines.append("| # | 问题 | overall | summary |")
            lines.append("|---|------|---------|---------|")
            for r in sorted(low_score, key=lambda x: x["quality_scores"]["overall"]):
                summary = r["quality_scores"].get("summary", "")
                lines.append(
                    f"| {r['id']} | {r['question'][:40]} | "
                    f"{r['quality_scores']['overall']:.2f} | {summary} |"
                )

    # --- 路由详情 ---
    lines.append("\n---\n")
    lines.append("## 路由评测详情\n")

    lines.append("| 题型 | 总数 | 路由正确 | 平均工具调用数 |")
    lines.append("|------|------|----------|--------------|")
    routing_by_type: dict[str, list[dict]] = {}
    for r in results:
        routing_by_type.setdefault(r["type"], []).append(r)
    for t in ["sql", "content", "mixed", "trend", "research", "reject"]:
        type_results = routing_by_type.get(t, [])
        if not type_results:
            continue
        correct = sum(1 for r in type_results if r["tool_routing_correct"])
        avg_tc = statistics.mean(r["tool_call_count"] for r in type_results)
        lines.append(
            f"| {t} | {len(type_results)} | {correct}/{len(type_results)} "
            f"({correct / len(type_results) * 100:.1f}%) | {avg_tc:.1f} |"
        )

    return "\n".join(lines)


async def run_eval() -> None:
    """并发运行评测：先跑 agent，再批量 judge"""
    questions_file = Path(__file__).parent / "questions.jsonl"
    questions = [json.loads(line) for line in questions_file.read_text().strip().split("\n")]
    total = len(questions)

    agent, checkpointer = build_agent(include_ask_user=False)
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def bounded_eval(q: dict) -> dict:
        async with semaphore:
            return await eval_one(agent, q)

    # 阶段 1：并发执行所有 agent 评测
    logger.info("阶段 1: Agent 评测开始，{} 题，并发数 {}", total, MAX_CONCURRENCY)
    results = await asyncio.gather(*(bounded_eval(q) for q in questions))
    results = sorted(results, key=lambda r: r["id"])

    # 阶段 2：批量 LLM-as-Judge 质量评分
    logger.info("阶段 2: LLM-as-Judge 质量评分")
    await judge_results(results, semaphore)

    # 路由统计
    correct_tool_routing = sum(1 for r in results if r["tool_routing_correct"])
    logger.info("=" * 60)
    logger.info(
        "评测完成: {}/{} 工具路由正确 ({:.1f}%)",
        correct_tool_routing,
        total,
        correct_tool_routing / total * 100,
    )

    # 质量评分统计
    scored = [r for r in results if r.get("quality_scores")]
    if scored:
        avg_overall = statistics.mean(r["quality_scores"]["overall"] for r in scored)
        logger.info(
            "质量评分: {}/{} 题, 平均 overall: {:.2f}/5.00", len(scored), total, avg_overall
        )

    # 生成报告
    report = _generate_report(results, total)
    report_dir = Path(__file__).parent.parent / "doc" / "eval"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"{now_str()}-eval-report.md"
    report_file.write_text(report, encoding="utf-8")
    logger.info("评测报告已保存到: {}", report_file)

    # 重命名内部字段为正式字段，保留完整回答和工具输出
    for r in results:
        if "_full_answer" in r:
            r["full_answer"] = r.pop("_full_answer")
        if "_tool_outputs_full" in r:
            r["tool_outputs_full"] = r.pop("_tool_outputs_full")

    output_file = Path(__file__).parent / "eval_results.json"
    output_file.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    logger.info("结果已保存到: {}", output_file)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M")


if __name__ == "__main__":
    asyncio.run(run_eval())
