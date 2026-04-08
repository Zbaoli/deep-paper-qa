"""评测覆盖分析脚本：分析题库覆盖情况，识别盲区"""

import json
from collections import Counter
from pathlib import Path


def analyze() -> None:
    """分析 questions.jsonl 的覆盖情况"""
    questions_file = Path(__file__).parent / "questions.jsonl"
    questions = [json.loads(line) for line in questions_file.read_text().strip().split("\n")]
    total = len(questions)

    print(f"题库总数: {total}")
    print()

    # 1. 题型分布
    type_dist = Counter(q["type"] for q in questions)
    print("=== 题型分布 ===")
    for t, cnt in type_dist.most_common():
        print(f"  {t:10s}: {cnt:3d} ({cnt / total * 100:.0f}%)")
    print()

    # 2. 期望工具分布
    tool_dist: Counter[str] = Counter()
    for q in questions:
        if "expected_tool" in q:
            tool_dist[q["expected_tool"]] += 1
        if "expected_tools" in q:
            for t in q["expected_tools"]:
                tool_dist[t] += 1
    print("=== 期望工具分布 ===")
    for t, cnt in tool_dist.most_common():
        print(f"  {t:20s}: {cnt:3d}")

    # 检查三个工具是否都被覆盖
    all_tools = {"execute_sql", "search_abstracts", "vector_search"}
    covered = set(tool_dist.keys())
    missing_tools = all_tools - covered
    if missing_tools:
        print(f"  ⚠️ 未覆盖工具: {missing_tools}")
    else:
        print("  ✓ 三个工具均有覆盖")
    print()

    # 3. 查询模式覆盖
    # 定义能力清单
    capabilities = {
        "execute_sql": {
            "简单聚合 (COUNT/AVG/MAX)": lambda q: any(
                kw in q.get("expected_sql_pattern", "") for kw in ["COUNT", "AVG", "MAX", "MIN"]
            ),
            "GROUP BY 分组统计": lambda q: "GROUP BY" in q.get("expected_sql_pattern", ""),
            "ORDER BY + LIMIT 排名": lambda q: (
                "ORDER BY" in q.get("expected_sql_pattern", "")
                or "LIMIT" in q.get("expected_sql_pattern", "")
            ),
            "数组 ANY() 查询": lambda q: (
                "ANY" in q.get("expected_sql_pattern", "") or "作者" in q["question"]
            ),
            "SQL 内全文检索 to_tsquery": lambda q: (
                "to_tsquery" in q.get("expected_sql_pattern", "")
                or "to_tsvector" in q.get("expected_sql_pattern", "")
            ),
            "WITH CTE 子查询": lambda q: (
                "WITH" in q.get("expected_sql_pattern", "")
                or "CASE" in q.get("expected_sql_pattern", "")
            ),
            "时间范围 BETWEEN": lambda q: (
                "year" in q.get("expected_sql_pattern", "").lower()
                and ("BETWEEN" in q["question"] or "到" in q["question"] or "趋势" in q["question"])
            ),
        },
        "search_abstracts": {
            "基础关键词搜索": lambda q: q.get("expected_tool") == "search_abstracts",
            "where 参数过滤": lambda q: (
                q.get("expected_tool") == "search_abstracts"
                and any(kw in q["question"] for kw in ["会议", "年", "引用"])
            ),
        },
        "vector_search": {
            "概念性/模糊查询": lambda q: q.get("expected_tool") == "vector_search",
            "where 参数过滤": lambda q: (
                "expected_tools" in q
                and "vector_search" in q.get("expected_tools", [])
                and any(kw in q["question"] for kw in ["会议", "年", "引用"])
            ),
        },
    }

    print("=== 能力覆盖 ===")
    uncovered: list[str] = []
    for tool_name, caps in capabilities.items():
        print(f"\n  [{tool_name}]")
        sql_questions = [
            q
            for q in questions
            if q.get("expected_tool") == tool_name or tool_name in q.get("expected_tools", [])
        ]
        for cap_name, check_fn in caps.items():
            matched = [q for q in sql_questions if check_fn(q)]
            status = f"✓ {len(matched)} 题" if matched else "✗ 未覆盖"
            print(f"    {cap_name:30s} {status}")
            if not matched:
                uncovered.append(f"{tool_name}: {cap_name}")
    print()

    # 4. 边界场景
    print("=== 边界场景 ===")
    edge_cases = {
        "空结果处理": lambda q: "CVPR" in q["question"] and "2026" in q["question"],
        "中英文混合": lambda q: any(kw in q["question"] for kw in ["思维链", "知识蒸馏", "多模态"]),
        "不存在的实体": lambda q: (
            "CVPR 2026" in q["question"] or "quantum" in q["question"].lower()
        ),
    }
    for case_name, check_fn in edge_cases.items():
        matched = [q for q in questions if check_fn(q)]
        status = f"✓ {len(matched)} 题" if matched else "✗ 未覆盖"
        print(f"  {case_name:25s} {status}")
    print()

    # 5. 盲区汇总
    if uncovered:
        print("=== 盲区汇总 ===")
        for gap in uncovered:
            print(f"  ⚠️ {gap}")
    else:
        print("=== 无明显盲区 ===")
    print()

    # 6. 逐题清单
    print("=== 题目清单 ===")
    for q in questions:
        tools = q.get("expected_tool", "") or "/".join(q.get("expected_tools", []))
        print(f"  #{q['id']:2d} [{q['type']:7s}] {tools:30s} {q['question'][:50]}")


if __name__ == "__main__":
    analyze()
