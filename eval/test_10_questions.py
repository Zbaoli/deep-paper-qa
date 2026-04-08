"""
生成 10 个问题，通过 Agent 提问，记录工具调用情况并分析合理性。
"""

import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from langchain_core.messages import HumanMessage
from deep_paper_qa.agent import build_agent

# 10 个测试问题，覆盖不同类型
QUESTIONS: list[dict] = [
    # --- SQL 类 (统计/计数/排名) ---
    {
        "id": 1,
        "question": "ACL 2025 收录了多少篇论文？",
        "type": "sql",
        "expected_tools": ["execute_sql"],
    },
    {
        "id": 2,
        "question": "哪个会议在 2024 年收录论文最多？",
        "type": "sql",
        "expected_tools": ["execute_sql"],
    },
    {
        "id": 3,
        "question": "引用量最高的 5 篇论文分别是哪些？",
        "type": "sql",
        "expected_tools": ["execute_sql"],
    },
    # --- 全文检索类 (关键词搜索) ---
    {
        "id": 4,
        "question": "有哪些关于 retrieval-augmented generation 的论文？",
        "type": "search",
        "expected_tools": ["search_abstracts"],
    },
    {
        "id": 5,
        "question": "有哪些论文研究了 chain-of-thought prompting？",
        "type": "search",
        "expected_tools": ["search_abstracts"],
    },
    # --- 向量检索类 (语义搜索 / 内容细节) ---
    {
        "id": 6,
        "question": "有哪些论文讨论了如何减少大语言模型的幻觉问题？",
        "type": "content",
        "expected_tools": ["search_abstracts"],
    },  # vector_search 可能不可用，降级到 search_abstracts
    # --- 混合类 (需要组合工具) ---
    {
        "id": 7,
        "question": "NeurIPS 2023 中引用量前 3 的论文讨论了什么主题？",
        "type": "mixed",
        "expected_tools": ["execute_sql", "search_abstracts"],
    },
    {
        "id": 8,
        "question": "2024 年关于 diffusion model 的论文主要发表在哪些会议？",
        "type": "mixed",
        "expected_tools": ["execute_sql"],
    },
    # --- 开放/复杂问题 ---
    {
        "id": 9,
        "question": "对比 2023 和 2024 年，各会议收录论文数量变化趋势如何？",
        "type": "sql",
        "expected_tools": ["execute_sql"],
    },
    {
        "id": 10,
        "question": "ICML 2025 有哪些关于 reinforcement learning 的高引论文？",
        "type": "mixed",
        "expected_tools": ["execute_sql", "search_abstracts"],
    },
]


@dataclass
class ToolCall:
    name: str
    input: str
    output: str = ""
    duration_s: float = 0.0


@dataclass
class QuestionResult:
    id: int
    question: str
    question_type: str
    expected_tools: list[str]
    actual_tools: list[ToolCall] = field(default_factory=list)
    final_answer: str = ""
    total_duration_s: float = 0.0
    tool_match: bool = False  # 工具调用是否符合预期


async def run_single_question(agent, question_cfg: dict) -> QuestionResult:
    """对单个问题执行 Agent 调用，收集工具调用信息。"""
    result = QuestionResult(
        id=question_cfg["id"],
        question=question_cfg["question"],
        question_type=question_cfg["type"],
        expected_tools=question_cfg["expected_tools"],
    )

    config = {
        "configurable": {"thread_id": f"eval-q{question_cfg['id']}"},
        "recursion_limit": 25,
    }

    current_tool: dict | None = None
    start = time.time()

    async for event in agent.astream_events(
        {"messages": [HumanMessage(content=question_cfg["question"])]},
        config=config,
        version="v2",
    ):
        kind = event.get("event", "")
        name = event.get("name", "")

        if kind == "on_tool_start":
            current_tool = {
                "name": name,
                "input": json.dumps(event.get("data", {}).get("input", {}), ensure_ascii=False)[
                    :500
                ],
                "start": time.time(),
            }

        elif kind == "on_tool_end" and current_tool:
            output_raw = str(event.get("data", {}).get("output", ""))
            tc = ToolCall(
                name=current_tool["name"],
                input=current_tool["input"],
                output=output_raw[:800],
                duration_s=round(time.time() - current_tool["start"], 2),
            )
            result.actual_tools.append(tc)
            current_tool = None

        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk", None)
            if chunk and hasattr(chunk, "content") and chunk.content:
                result.final_answer += chunk.content

    result.total_duration_s = round(time.time() - start, 2)

    # 判断工具是否匹配
    actual_tool_names = set(tc.name for tc in result.actual_tools)
    expected = set(result.expected_tools)
    # 宽松匹配：预期工具都被调用了就算匹配（允许额外调用）
    result.tool_match = expected.issubset(actual_tool_names)

    return result


async def main():
    agent, _ = build_agent()

    results: list[QuestionResult] = []
    for q in QUESTIONS:
        print(f"\n{'=' * 60}")
        print(f"Q{q['id']}: {q['question']}")
        print(f"类型: {q['type']} | 预期工具: {q['expected_tools']}")
        print("-" * 60)

        try:
            r = await run_single_question(agent, q)
        except Exception as e:
            r = QuestionResult(
                id=q["id"],
                question=q["question"],
                question_type=q["type"],
                expected_tools=q["expected_tools"],
                final_answer=f"[ERROR] {type(e).__name__}: {e}",
                total_duration_s=round(time.time() - time.time(), 2),
            )
            print(f"  ❌ 错误: {e}")
        results.append(r)

        # 实时输出
        for tc in r.actual_tools:
            print(f"  🔧 {tc.name} ({tc.duration_s}s)")
            print(f"     输入: {tc.input[:200]}")
            print(f"     输出: {tc.output[:200]}")

        print(f"\n  ✅ 工具匹配: {r.tool_match}")
        print(f"  ⏱  耗时: {r.total_duration_s}s")
        print(f"  📝 回答: {r.final_answer[:300]}...")

    # 汇总统计
    print("\n" + "=" * 60)
    print("📊 汇总统计")
    print("=" * 60)
    match_count = sum(1 for r in results if r.tool_match)
    print(f"工具匹配率: {match_count}/{len(results)} ({match_count / len(results) * 100:.0f}%)")

    for r in results:
        actual = [tc.name for tc in r.actual_tools]
        status = "✅" if r.tool_match else "❌"
        print(
            f"  {status} Q{r.id} [{r.question_type}] "
            f"预期={r.expected_tools} 实际={actual} ({r.total_duration_s}s)"
        )

    # 保存详细结果
    output_path = "eval/test_10_results.json"
    serializable = []
    for r in results:
        d = {
            "id": r.id,
            "question": r.question,
            "question_type": r.question_type,
            "expected_tools": r.expected_tools,
            "actual_tools": [asdict(tc) for tc in r.actual_tools],
            "final_answer": r.final_answer,
            "total_duration_s": r.total_duration_s,
            "tool_match": r.tool_match,
        }
        serializable.append(d)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存到 {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
