# 10 问题测试报告：工具调用分析

**测试时间**: 2026-04-01  
**Agent**: DeepSeek-chat via LangGraph ReAct  
**数据库**: 81,913 篇论文，10 个 AI 顶会 (2020-2025)

---

## 一、测试结果汇总

| # | 问题 | 类型 | 预期工具 | 实际工具调用 | 匹配 | 耗时 |
|---|------|------|----------|-------------|------|------|
| 1 | ACL 2025 收录了多少篇论文？ | sql | execute_sql | execute_sql ×1 | ✅ | 7.5s |
| 2 | 哪个会议在 2024 年收录论文最多？ | sql | execute_sql | execute_sql ×1 | ✅ | 12.0s |
| 3 | 引用量最高的 5 篇论文？ | sql | execute_sql | execute_sql ×1 | ✅ | 24.0s |
| 4 | 关于 RAG 的论文？ | search | search_abstracts | execute_sql ×2 + search_abstracts ×1 | ✅ | 37.3s |
| 5 | chain-of-thought prompting 论文？ | search | search_abstracts | search_abstracts ×2 + execute_sql ×2 | ✅ | 59.9s |
| 6 | 减少 LLM 幻觉的论文？ | content | search_abstracts | search_abstracts ×3 + execute_sql ×1 | ✅ | 54.2s |
| 7 | NeurIPS 2023 高引前 3 主题？ | mixed | execute_sql + search_abstracts | execute_sql ×1 + vector_search ×1 + search_abstracts ×4 | ✅ | 51.6s |
| 8 | 2024 diffusion model 各会议分布？ | mixed | execute_sql | search_abstracts ×1 + execute_sql ×3 | ✅ | 50.4s |
| 9 | 2023 vs 2024 各会议论文变化趋势？ | sql | execute_sql | execute_sql ×3 | ✅ | 50.1s |
| 10 | ICML 2025 RL 高引论文？ | mixed | execute_sql + search_abstracts | **递归超限 (25 步)** | ❌ | - |

**工具匹配率**: 9/10 (90%)  
**平均耗时**: ~39.5s（排除 Q10）

---

## 二、逐题分析

### Q1: ACL 2025 收录了多少篇论文？ ✅
- **工具调用**: `execute_sql("SELECT COUNT(*) FROM papers WHERE year=2025 AND conference='ACL'")`
- **结果**: 1,698 篇
- **合理性**: ⭐⭐⭐⭐⭐ 完美。简单计数直接用 SQL，一次调用即得答案。

### Q2: 哪个会议在 2024 年收录论文最多？ ✅
- **工具调用**: `execute_sql("SELECT conference, COUNT(*) ... WHERE year=2024 GROUP BY conference ORDER BY ... DESC")`
- **结果**: NeurIPS 4,035 篇排第一
- **合理性**: ⭐⭐⭐⭐⭐ 完美。GROUP BY + ORDER BY 是正确的 SQL 策略。

### Q3: 引用量最高的 5 篇论文？ ✅
- **工具调用**: `execute_sql("SELECT title, authors, year, conference, citations FROM papers ORDER BY citations DESC LIMIT 5")`
- **结果**: ViT (21,100), SimCLR (7,301), DDPM (5,549), CLIP (5,296), Informer (5,203)
- **合理性**: ⭐⭐⭐⭐⭐ 完美。排名查询直接用 SQL。

### Q4: 关于 RAG 的论文？ ✅ (有冗余)
- **工具调用序列**:
  1. `execute_sql` — 查 directions 含 RAG 的统计（仅 13 篇）
  2. `search_abstracts` — 全文搜索 "retrieval-augmented generation OR RAG"
  3. `execute_sql` — 再查 directions 含 RAG 的论文列表
- **合理性**: ⭐⭐⭐ 中等。预期只需 `search_abstracts` 即可，但 Agent 额外用了 2 次 SQL 来从 directions 字段角度补充。第 1 和第 3 次 SQL 有重复——先查了 COUNT 再查了详情，可以合并。不过多角度搜索确实能提高召回率。

### Q5: chain-of-thought prompting 论文？ ✅ (有冗余)
- **工具调用序列**:
  1. `search_abstracts` — "chain-of-thought" prompting
  2. `search_abstracts` — CoT prompting 变体搜索
  3. `execute_sql` — 查 directions 含 CoT 的统计
  4. `execute_sql` — 查 directions 含 CoT 的论文详情
- **合理性**: ⭐⭐⭐ 中等。搜索了两轮关键词变体（chain-of-thought, CoT）是合理的，但额外又做了两次 SQL 查询显得冗余。总共 4 次调用导致耗时接近 60s。

### Q6: 减少 LLM 幻觉的论文？ ✅
- **工具调用序列**:
  1. `search_abstracts` — "hallucination reduction OR mitigation"
  2. `search_abstracts` — "reduce hallucination OR detection OR factuality"
  3. `search_abstracts` — "contrastive decoding OR self-consistency"
  4. `execute_sql` — 查 directions 含 Hallucination/Factuality 的统计
- **合理性**: ⭐⭐⭐⭐ 良好。幻觉问题涉及多种方法（检测、缓解、对比解码等），多轮搜索是合理的。最后用 SQL 补充统计视角也有价值。

### Q7: NeurIPS 2023 高引前 3 主题？ ✅
- **工具调用序列**:
  1. `execute_sql` — 查 NeurIPS 2023 引用前 3：LLaVA, ToT, QLoRA
  2. `vector_search` — 搜 LLaVA（RAG 服务不可用，返回 404）
  3. `search_abstracts` — "Visual Instruction Tuning" LLaVA（降级搜索）
  4. `search_abstracts` — "Tree of Thoughts"
  5. `search_abstracts` — "QLoRA efficient finetuning"（未命中目标论文）
  6. `search_abstracts` — "QLoRA quantization low-rank"（仍未精确命中）
- **合理性**: ⭐⭐⭐⭐ 良好。策略正确：先 SQL 定位高引论文，再搜索了解内容。vector_search 失败后正确降级到 search_abstracts。但 QLoRA 搜索两次都未命中（该论文可能不在库中），Agent 应更早放弃并利用已有的 directions/abstract 信息。

### Q8: 2024 diffusion model 各会议分布？ ✅ (有冗余)
- **工具调用序列**:
  1. `search_abstracts` — 先搜索 diffusion model（不太必要）
  2. `execute_sql` — 查 2024 各会议总论文数
  3. `execute_sql` — 查 2024 diffusion 论文按会议分布
  4. `execute_sql` — 查占比（total + diffusion + percentage）
- **合理性**: ⭐⭐⭐ 中等。这本质上是个统计问题，第 1 次 search_abstracts 不必要。3 次 SQL 查询中，第 2 和第 3 次可以合并，第 4 次的占比计算也可以一次 SQL 搞定。不过最终结果很详尽（包含占比），用户体验好。

### Q9: 2023 vs 2024 各会议论文变化趋势？ ✅
- **工具调用序列**:
  1. `execute_sql` — GROUP BY conference, year WHERE year IN (2023,2024)
  2. `execute_sql` — 尝试 WITH CTE 做 pivot（被 SQL 校验拦截！）
  3. `execute_sql` — 改用 SUM(CASE WHEN) 做列转行+计算变化
- **合理性**: ⭐⭐⭐⭐ 良好。第 1 次查了原始数据，第 2 次尝试 CTE 被拦截（execute_sql 只允许 SELECT 开头，WITH ... AS 被误判），第 3 次成功绕过限制。暴露了 SQL 校验的一个 bug：`WITH ... AS (...) SELECT` 是合法的只读查询但被拦截了。

### Q10: ICML 2025 RL 高引论文？ ❌ (递归超限)
- **从日志可见的工具调用**:
  1. `execute_sql` — directions 含 'reinforcement learning' 的 ICML 2025 论文（0 条！）
  2. `execute_sql` — ICML 2025 总论文数
  3. `search_abstracts` — "reinforcement learning OR RL ICML 2025"
  4. `search_abstracts` — "reinforcement learning" ICML 2025（带引号）
  5. `execute_sql` — ICML 2025 引用前 20 的论文（尝试从高引论文中找 RL 相关的）
  6. `execute_sql` — 查某篇论文详情
  7. `search_abstracts` — "reinforcement learning" ICML 2025 -survey
  8. `search_abstracts` — "reinforcement learning OR RL 2025"
  9. ...继续循环直到 25 步超限
- **合理性**: ⭐⭐ 较差。Agent 陷入了"搜不到精确结果→换个方式再搜"的循环。核心问题是 directions 标签中没有 "reinforcement learning" 的精确匹配，全文搜索也难以在指定会议范围内筛选。Agent 缺乏"及时止损"的能力，应在 3-4 次尝试后给出"现有数据中未找到精确匹配"的结论。

---

## 三、问题发现

### 1. 工具调用冗余 (Q4, Q5, Q8)
Agent 倾向于"多角度验证"，对同一问题从 search_abstracts 和 execute_sql 两个维度反复查询。这提高了召回率但显著增加了延迟（单次 search_abstracts 约 2s，单次 execute_sql 约 0.05s，但 LLM 思考时间 5-10s/轮）。

**建议**: 在 prompt 中加入"尽量减少工具调用次数，优先用一次查询获取足够信息"的指导。

### 2. 递归超限 (Q10)
当搜索结果不理想时，Agent 不断尝试新的查询策略而不收敛。recursion_limit=25 仍不够。

**建议**: 
- 在 prompt 中加入"如果 3 次工具调用后仍无满意结果，直接基于已有信息回答并说明局限"
- 或在 Agent 层面设置最大工具调用次数

### 3. SQL 校验误拦 (Q9)
`WITH ... AS (...) SELECT ...` 是合法的只读 SQL，但被 execute_sql 的正则校验拦截。

**建议**: 修改 SQL 校验逻辑，允许 `WITH` 开头的 CTE 查询。

### 4. search_abstracts 精度不足
全文搜索（基于 PostgreSQL tsvector）对长短语和特定领域术语的匹配不够精确，相关度分数普遍偏低（0.05-0.10）。

**建议**: 考虑使用 ts_rank_cd 替代 ts_rank，或引入语义搜索兜底。

### 5. vector_search 不可用
RAG API 返回 404，所有语义搜索降级到 search_abstracts。Agent 正确处理了降级逻辑。

---

## 四、总体评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 工具选择正确性 | ⭐⭐⭐⭐ | 9/10 题选对了工具，策略基本合理 |
| 工具调用效率 | ⭐⭐⭐ | 平均 2.7 次/题，多数题存在 1-2 次冗余调用 |
| 错误恢复能力 | ⭐⭐⭐⭐ | vector_search 失败后正确降级；SQL 被拦后能改写 |
| 收敛能力 | ⭐⭐ | Q10 无法收敛，陷入无限循环 |
| 回答质量 | ⭐⭐⭐⭐ | 答案准确、有结构、引用了论文 ID 和标题 |
| 响应速度 | ⭐⭐ | 平均 39.5s/题偏慢，主要瓶颈是 LLM 思考时间 |

**总评**: Agent 在简单 SQL 查询（Q1-Q3）上表现出色，一次调用即得答案。搜索类问题（Q4-Q6）工具选择正确但调用次数偏多。混合类问题（Q7-Q9）策略合理但效率有优化空间。最大风险是 Q10 暴露的"无法收敛"问题，需要在 prompt 或架构层面增加终止条件。
