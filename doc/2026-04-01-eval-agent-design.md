# eval-agent Skill 设计文档

**日期**: 2026-04-01
**类型**: 项目专属 Claude Code Skill
**路径**: `.claude/skills/eval-agent/SKILL.md`

---

## 概述

一键评测 deep_paper_qa Agent 的 skill：自动分析题库覆盖盲区、补充测试样本、运行评测、分析轨迹数据、生成优化报告和具体代码修改方案。

**目标用户**: 项目作者，在 Claude Code 中通过 `/eval-agent` 触发。

## 流程设计

### 阶段 1：覆盖分析

- 读取 `eval/questions.jsonl`，统计题型分布（sql / content / mixed）
- 读取 agent 的 3 个 tool 定义（execute_sql, search_abstracts, vector_search），识别哪些工具能力未被测试覆盖
- 分析维度：
  - 题型比例
  - 工具覆盖
  - 查询复杂度（单工具 / 多工具 / 多轮）
  - 边界场景（空结果、错误恢复、递归超限）
- 输出覆盖盲区清单

### 阶段 2：补充测试样本

- 针对盲区生成新的评测题，追加到 `eval/questions.jsonl`
- 遵循现有 JSONL 格式（id / type / question / expected_tool(s)）
- 全自动，无需人工确认，直接根据盲区分析结果生成
- 单次最多补 10 道题

### 阶段 3：运行评测

- 执行 `uv run python eval/run_eval.py`
- 超时 30 分钟，超时则用已完成的结果继续分析
- 收集 `eval/eval_results.json`

### 阶段 4：轨迹分析

**数据源 1 — 评测结果（主）**：解析 `eval/eval_results.json`

**数据源 2 — 线上日志（补充）**：解析 `logs/*.jsonl`，只取最近 7 天

**分析维度**：
- 工具路由正确性（按题型统计）
- 调用效率（冗余调用、平均次数/题）
- 延迟分布（总耗时、工具耗时 vs LLM 思考耗时）
- 错误模式（递归超限、工具失败、降级行为）
- 回答质量（长度、是否引用数据）

### 阶段 5：生成报告

**输出路径**: `doc/eval/YYYY-MM-DD_HH-MM-eval-report.md`

**报告结构**：
1. 测试概况（题数、通过率、耗时）
2. 逐题分析（工具调用序列、合理性评分）
3. 问题发现（按严重程度排序）
4. 优化建议 + 具体代码修改方案（unified diff 格式，标注文件和行号）
5. 与上次报告的对比（读取 `doc/eval/` 最近一份；首次运行跳过）

## 约束

| 约束项 | 值 |
|--------|-----|
| 评测超时 | 30 分钟 |
| 线上日志范围 | 最近 7 天 |
| 单次补题上限 | 10 道 |
| 修改方案格式 | unified diff，标注文件和行号 |
| 人工确认 | 无，全自动（适配 `/loop` 循环执行） |
| Skill 位置 | `.claude/skills/eval-agent/SKILL.md`（项目专属） |

## 涉及的文件

| 文件 | 用途 |
|------|------|
| `eval/questions.jsonl` | 读取+追加评测题 |
| `eval/run_eval.py` | 执行评测 |
| `eval/eval_results.json` | 评测结果 |
| `logs/*.jsonl` | 线上对话轨迹 |
| `src/deep_paper_qa/agent.py` | Agent 定义 |
| `src/deep_paper_qa/prompts.py` | System prompt |
| `src/deep_paper_qa/tools/*.py` | 3 个工具定义 |
| `doc/eval/*.md` | 输出报告 + 历史对比 |
