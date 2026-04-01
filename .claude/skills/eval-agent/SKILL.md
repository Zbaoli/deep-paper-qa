---
name: eval-agent
description: Use when evaluating the deep_paper_qa agent — analyzes test coverage gaps, generates new test samples, runs evaluation, analyzes execution traces, and produces optimization reports with concrete code change proposals to doc/eval/
---

# eval-agent

全自动评测 deep_paper_qa Agent：覆盖分析 → 补题 → 运行评测 → 轨迹分析 → 生成报告。无需人工确认，适配 `/loop` 循环执行。

## 阶段 1：覆盖分析

读取 `eval/questions.jsonl`，分析题库覆盖情况：

**统计维度：**
- 题型分布：sql / content / mixed 各多少道
- 工具覆盖：execute_sql / search_abstracts / vector_search 是否都被测到
- 查询复杂度：单工具 / 多工具 / 多轮调用
- 边界场景：空结果、错误恢复（SQL 语法错误、服务不可用）、递归超限

**3 个工具的能力清单（用于比对覆盖度）：**

execute_sql:
- 简单聚合（COUNT / AVG / MAX / MIN）
- GROUP BY 分组统计
- ORDER BY + LIMIT 排名
- 数组字段 ANY() 查询（authors）
- 全文检索 to_tsquery 在 SQL 内使用
- WITH CTE 子查询
- 多条件组合 WHERE
- 时间范围 BETWEEN

search_abstracts:
- 基础关键词搜索
- OR / 引号 / 排除词语法
- where 参数按元数据过滤（年份、会议、引用量、作者）
- 同义词扩展查询

vector_search:
- 概念性/模糊查询
- where 参数按元数据过滤
- top_k 控制返回数量
- 降级场景（Embedding 服务不可用时提示用 search_abstracts）

**输出：** 覆盖盲区清单，列出未被测试的工具能力和场景。

## 阶段 2：补充测试样本

根据阶段 1 的盲区清单，自动生成补充评测题，追加到 `eval/questions.jsonl`。

**规则：**
- 单次最多补 10 道题
- id 从现有最大值 +1 递增
- 格式与现有题目一致：
  - sql 类型：`{"id": N, "type": "sql", "question": "...", "expected_tool": "execute_sql"}`
  - content 类型：`{"id": N, "type": "content", "question": "...", "expected_tool": "vector_search"}`（或 `"search_abstracts"`）
  - mixed 类型：`{"id": N, "type": "mixed", "question": "...", "expected_tools": ["execute_sql", "vector_search"]}`
- 题目用中文，贴近真实用户提问风格
- 优先补充覆盖盲区，不重复已有题目的意图

## 阶段 3：运行评测

```bash
uv run python eval/run_eval.py
```

- 超时 30 分钟（`timeout 1800`）
- 超时则用已产出的 `eval/eval_results.json` 继续分析
- 如果 `eval/eval_results.json` 不存在且评测超时，在报告中标注"评测未完成"

## 阶段 4：轨迹分析

### 数据源 1（主）：评测结果

读取 `eval/eval_results.json`，提取：
- 每道题的工具调用序列、每次调用的输入/输出/耗时
- 工具路由是否正确（actual vs expected）
- 总耗时

### 数据源 2（补充）：线上日志

读取 `logs/*.jsonl`，只取最近 7 天的文件（按文件名或修改时间判断）。提取：
- 真实用户的提问模式
- 工具调用模式是否与评测一致
- 异常事件（tool 报错、超时、降级）

### 分析维度

| 维度 | 指标 |
|------|------|
| 工具路由正确性 | 按题型统计正确率 |
| 调用效率 | 平均调用次数/题、冗余调用识别（同一工具相似输入被调用多次） |
| 延迟分布 | 总耗时、工具耗时、LLM 思考耗时（总耗时 - 工具耗时之和） |
| 错误模式 | 递归超限、工具失败、SQL 校验误拦、降级行为 |
| 回答质量 | 回答长度、是否引用了论文 ID/标题、是否包含数据支撑 |

## 阶段 5：生成报告

**输出路径：** `doc/eval/YYYY-MM-DD_HH-MM-eval-report.md`（取当前时间精确到分钟）

**报告结构：**

```markdown
# Agent 评测报告

**时间**: YYYY-MM-DD HH:MM
**题目数**: N（原有 M + 新增 K）
**工具路由正确率**: X/N (XX.X%)
**平均耗时**: XX.Xs/题

---

## 一、测试概况
[按题型的通过率表格]

## 二、覆盖分析
[本次发现的盲区 + 补充的题目清单]

## 三、逐题分析
[每道题的工具调用序列、合理性评分 ⭐1-5、问题标注]

## 四、问题发现
[按严重程度排序：致命 > 重要 > 改进]

## 五、优化建议
[每条建议包含：]
- 问题描述
- 影响范围
- 具体修改方案（unified diff 格式，标注文件路径和行号）
- 预期效果

## 六、趋势对比
[与 doc/eval/ 下最近一份报告对比：正确率变化、耗时变化、新增/修复的问题]
[首次运行无历史时跳过此节]
```

**修改方案示例格式：**

````markdown
**建议 1：允许 WITH CTE 查询**

影响：Q9 类型的复杂统计查询被误拦

```diff
--- a/src/deep_paper_qa/tools/execute_sql.py
+++ b/src/deep_paper_qa/tools/execute_sql.py
@@ -17,1 +17,1 @@
-_SELECT_PATTERN = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
+_SELECT_PATTERN = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
```

预期：CTE 查询不再被拦截，复杂统计场景工具调用次数减少
````

## 注意事项

- 全程不使用 AskUserQuestion，不等待人工输入
- 如果 `eval/run_eval.py` 执行出错（非超时），在报告中记录错误信息并跳过阶段 3，用已有的历史评测结果（如有）继续分析
- 报告中所有 diff 方案基于当前代码的实际内容生成，先 Read 相关文件再写 diff
- `doc/eval/` 目录不存在时自动创建
