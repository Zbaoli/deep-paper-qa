"""路由分类准确性测试：100 题覆盖六种类别"""

import asyncio
import json
from collections import Counter
from datetime import datetime

from deep_paper_qa.pipelines.router import classify_question

# 100 个测试问题，每类预期若干题
TEST_QUESTIONS = [
    # ── reject（15 题）──
    {"q": "今天天气怎么样？", "expected": "reject"},
    {"q": "帮我写一段 Python 排序代码", "expected": "reject"},
    {"q": "帮我润色一下我的论文摘要", "expected": "reject"},
    {"q": "推荐一部好看的电影", "expected": "reject"},
    {"q": "明天股市会涨吗？", "expected": "reject"},
    {"q": "怎么做红烧肉？", "expected": "reject"},
    {"q": "你是谁开发的？", "expected": "reject"},
    {"q": "帮我翻译这段话", "expected": "reject"},
    {"q": "北京到上海的火车票多少钱？", "expected": "reject"},
    {"q": "请帮我写一封求职信", "expected": "reject"},
    {"q": "JavaScript 和 TypeScript 有什么区别？", "expected": "reject"},
    {"q": "如何学好英语？", "expected": "reject"},
    {"q": "给我讲个笑话", "expected": "reject"},
    {"q": "2024年奥运会在哪举办？", "expected": "reject"},
    {"q": "帮我算一下 123 * 456", "expected": "reject"},
    # ── general（30 题）──
    {"q": "ACL 2025 有多少篇论文？", "expected": "general"},
    {"q": "2024年NeurIPS收录了多少篇论文？", "expected": "general"},
    {"q": "各会议论文数量是多少？", "expected": "general"},
    {"q": "引用数最高的10篇论文是哪些？", "expected": "general"},
    {"q": "有哪些关于 RAG 的论文？", "expected": "general"},
    {"q": "有哪些关于 Chain-of-Thought prompting 的论文？", "expected": "general"},
    {"q": "2024年引用最高的 RAG 论文讲了什么？", "expected": "general"},
    {"q": "Hinton 近两年发了什么论文？", "expected": "general"},
    {"q": "ICLR 2023 关于 RLHF 的论文有几篇？", "expected": "general"},
    {"q": "推荐一些高引用的大语言模型论文", "expected": "general"},
    {"q": "NeurIPS 2024 关于多模态的论文有哪些？", "expected": "general"},
    {"q": "哪个会议发表的论文数量最多？", "expected": "general"},
    {"q": "预印本和会议论文的比例是多少？", "expected": "general"},
    {"q": "合著作者最多的论文是哪篇？", "expected": "general"},
    {"q": "EMNLP 2024 的平均引用数是多少？", "expected": "general"},
    {"q": "关于 FlashAttention 的论文有哪些？", "expected": "general"},
    {"q": "找一下关于模型量化的论文", "expected": "general"},
    {"q": "ICML 2024 收了哪些关于强化学习的论文？", "expected": "general"},
    {"q": "Yann LeCun 发了哪些论文？", "expected": "general"},
    {"q": "有没有关于 Mixture of Experts 的论文？", "expected": "general"},
    {"q": "引用超过 100 的论文有多少篇？", "expected": "general"},
    {"q": "KDD 和 WWW 哪个会议论文更多？", "expected": "general"},
    {"q": "2025年有多少篇关于 LLM 的论文？", "expected": "general"},
    {"q": "AAAI 2024 的论文主要关注什么方向？", "expected": "general"},
    {"q": "搜索一下关于代码生成的论文", "expected": "general"},
    {"q": "有没有关于图神经网络的论文？", "expected": "general"},
    {"q": "最近有什么关于 prompt engineering 的论文？", "expected": "general"},
    {"q": "哪些论文讨论了 LLM 的幻觉问题？", "expected": "general"},
    {"q": "NAACL 2024 有多少篇论文？", "expected": "general"},
    {"q": "关于 diffusion model 的高引论文有哪些？", "expected": "general"},
    # ── research（20 题）──
    {"q": "调研 AI for Science 在蛋白质结构预测方向的最新进展", "expected": "research"},
    {"q": "总结 2023-2025 年 LLM Agent 的研究脉络", "expected": "research"},
    {"q": "梳理 text-to-image 从 GAN 到 diffusion 的技术演进", "expected": "research"},
    {"q": "写一份关于多模态大模型的研究综述", "expected": "research"},
    {"q": "调研 RLHF 的替代方案，包括 DPO、KTO 等方法的优劣", "expected": "research"},
    {"q": "总结 AI 在药物发现领域的应用进展", "expected": "research"},
    {"q": "梳理大模型推理优化的研究脉络，包括量化、蒸馏、剪枝", "expected": "research"},
    {"q": "综述 Retrieval-Augmented Generation 的研究现状和未来方向", "expected": "research"},
    {"q": "调研自动驾驶感知领域最近的技术突破", "expected": "research"},
    {"q": "总结 Transformer 架构从 NLP 扩展到视觉领域的演进历程", "expected": "research"},
    {"q": "写一份关于联邦学习隐私保护的综述报告", "expected": "research"},
    {"q": "调研代码大模型的最新进展，包括训练方法和评测基准", "expected": "research"},
    {"q": "梳理 few-shot learning 到 in-context learning 的发展脉络", "expected": "research"},
    {"q": "综述 AI 可解释性研究的主要方法和挑战", "expected": "research"},
    {"q": "调研知识图谱与大语言模型结合的研究方向", "expected": "research"},
    {"q": "总结多智能体协作的研究进展和关键论文", "expected": "research"},
    {"q": "写一份 AI 安全对齐的研究综述", "expected": "research"},
    {"q": "梳理视觉语言模型从 CLIP 到 GPT-4V 的技术路线", "expected": "research"},
    {"q": "调研低资源语言 NLP 的最新研究方法", "expected": "research"},
    {"q": "综述强化学习在机器人控制中的应用进展", "expected": "research"},
    # ── trend（15 题）──
    {"q": "RAG 近三年的发展趋势怎么样？", "expected": "trend"},
    {"q": "知识蒸馏这个方向是在升温还是降温？", "expected": "trend"},
    {"q": "2020-2025 年 GAN 相关论文的数量变化", "expected": "trend"},
    {"q": "Transformer 架构改进的研究热度变化", "expected": "trend"},
    {"q": "多模态大模型近几年论文数量趋势如何？", "expected": "trend"},
    {"q": "强化学习这几年的论文数量是增还是减？", "expected": "trend"},
    {"q": "联邦学习的研究热度近年来有什么变化？", "expected": "trend"},
    {"q": "NLP 领域 prompt engineering 的研究趋势", "expected": "trend"},
    {"q": "图神经网络的研究热度在下降吗？", "expected": "trend"},
    {"q": "自监督学习这几年发展趋势怎么样？", "expected": "trend"},
    {"q": "对比学习的论文数量近年有什么变化？", "expected": "trend"},
    {"q": "AI 生成内容（AIGC）的研究趋势", "expected": "trend"},
    {"q": "模型量化这个方向近三年热不热？", "expected": "trend"},
    {"q": "注意力机制优化的研究趋势如何？", "expected": "trend"},
    {"q": "数据增强方法的论文数量变化趋势", "expected": "trend"},
    # ── reading（10 题）──
    {"q": "帮我精读 Attention Is All You Need", "expected": "reading"},
    {"q": "详细解读 FlashAttention 论文的方法部分", "expected": "reading"},
    {"q": "这篇 DPO 论文的核心贡献是什么？", "expected": "reading"},
    {"q": "帮我读一下 BERT 这篇论文", "expected": "reading"},
    {"q": "解读 GPT-4 的技术报告", "expected": "reading"},
    {"q": "帮我精读 LoRA 论文，重点看方法和实验", "expected": "reading"},
    {"q": "逐章节解读 ResNet 论文", "expected": "reading"},
    {"q": "详细分析 InstructGPT 这篇论文的训练流程", "expected": "reading"},
    {"q": "精读 Chain-of-Thought Prompting 的原始论文", "expected": "reading"},
    {"q": "帮我读一下 Mixtral 8x7B 的技术报告", "expected": "reading"},
    # ── compare（10 题）──
    {"q": "对比 DPO 和 RLHF 这两篇论文的方法差异", "expected": "compare"},
    {"q": "FlashAttention v1 和 v2 有什么改进？", "expected": "compare"},
    {"q": "对比 BERT 和 GPT 的架构差异", "expected": "compare"},
    {"q": "LoRA 和 QLoRA 的方法对比", "expected": "compare"},
    {"q": "对比 Mamba 和 Transformer 这两篇论文", "expected": "compare"},
    {"q": "CLIP 和 BLIP 的方法有什么不同？", "expected": "compare"},
    {"q": "对比 RAG 和 REALM 的检索方法", "expected": "compare"},
    {"q": "ResNet 和 ViT 的架构对比分析", "expected": "compare"},
    {"q": "对比 PPO 和 DPO 的训练方法差异", "expected": "compare"},
    {"q": "SAM 和 Segment Anything 2 有什么改进？", "expected": "compare"},
]


async def run_test():
    """运行路由分类测试"""
    results = []
    total = len(TEST_QUESTIONS)

    print(f"开始路由分类测试，共 {total} 题...\n")

    for i, item in enumerate(TEST_QUESTIONS):
        q = item["q"]
        expected = item["expected"]
        try:
            actual = await classify_question(q)
            actual_val = actual.value
        except Exception as e:
            actual_val = f"ERROR: {e}"

        correct = actual_val == expected
        results.append(
            {
                "id": i + 1,
                "question": q,
                "expected": expected,
                "actual": actual_val,
                "correct": correct,
            }
        )

        status = "✓" if correct else "✗"
        if not correct:
            print(f"  {status} #{i + 1} [{expected}→{actual_val}] {q}")

    # 统计
    total_correct = sum(1 for r in results if r["correct"])
    print(f"\n{'=' * 60}")
    print(f"总体准确率: {total_correct}/{total} ({total_correct / total * 100:.1f}%)\n")

    # 按类别统计
    by_expected = {}
    for r in results:
        by_expected.setdefault(r["expected"], []).append(r)

    print(f"{'类别':<12} {'题数':>4} {'正确':>4} {'准确率':>8}")
    print("-" * 36)
    for cat in ["reject", "general", "research", "trend", "reading", "compare"]:
        items = by_expected.get(cat, [])
        correct_count = sum(1 for r in items if r["correct"])
        acc = correct_count / len(items) * 100 if items else 0
        print(f"{cat:<12} {len(items):>4} {correct_count:>4} {acc:>7.1f}%")

    # 混淆分析：被误分到哪里
    print(f"\n{'=' * 60}")
    print("误分类详情：\n")
    wrong = [r for r in results if not r["correct"]]
    if not wrong:
        print("无误分类！")
    else:
        confusion = Counter()
        for r in wrong:
            confusion[(r["expected"], r["actual"])] += 1
        for (exp, act), count in sorted(confusion.items(), key=lambda x: -x[1]):
            print(f"  {exp} → {act}: {count} 题")

    # 保存结果
    output = {
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "correct": total_correct,
        "accuracy": round(total_correct / total * 100, 1),
        "results": results,
    }
    with open("eval/router_test_results.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("\n详细结果已保存到 eval/router_test_results.json")


if __name__ == "__main__":
    asyncio.run(run_test())
