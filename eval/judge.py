"""LLM-as-Judge 评分逻辑：调用 LLM 对 agent 回答进行多维度质量评分"""

import json
import re
from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from deep_paper_qa.config import settings
from eval.judge_prompt import (
    JUDGE_SYSTEM_PROMPT,
    JUDGE_USER_TEMPLATE,
    SCORE_DIMENSIONS,
)


def _build_client() -> AsyncOpenAI:
    """构建 OpenAI 兼容客户端"""
    return AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)


def _parse_judge_response(text: str) -> dict[str, Any] | None:
    """从 LLM 响应中解析 JSON 评分结果。

    解析策略：
    1. 直接 json.loads
    2. 正则提取第一个 {...} JSON 块（处理 markdown fence）
    3. 失败返回 None
    """
    # 策略 1：直接解析
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 策略 2：正则提取 JSON 块
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def _validate_scores(data: dict[str, Any]) -> dict[str, Any] | None:
    """校验评分数据格式，确保所有维度都有有效分数"""
    for dim in SCORE_DIMENSIONS:
        if dim not in data:
            return None
        dim_data = data[dim]
        if not isinstance(dim_data, dict) or "score" not in dim_data:
            return None
        score = dim_data["score"]
        if not isinstance(score, (int, float)) or score < 1 or score > 5:
            return None
    return data


def _compute_overall(scores: dict[str, Any]) -> float:
    """计算 overall 分数（四维度算术平均）"""
    total = sum(scores[dim]["score"] for dim in SCORE_DIMENSIONS)
    return round(total / len(SCORE_DIMENSIONS), 2)


async def judge_answer(
    question: str,
    question_type: str,
    answer: str,
    tool_outputs: str,
    tool_call_count: int = 0,
    tool_call_summary: str = "",
) -> dict[str, Any] | None:
    """对 agent 回答进行 LLM-as-Judge 质量评分。

    Args:
        question: 用户问题
        question_type: 问题类型（sql/content/mixed）
        answer: agent 的完整回答
        tool_outputs: 工具返回的原始输出（拼接后的文本）
        tool_call_count: 工具调用总次数
        tool_call_summary: 工具调用序列摘要（如 "1. execute_sql(sql=...) 2. search_abstracts(query=...)"）

    Returns:
        评分字典（含 accuracy/completeness/citation/clarity/efficiency/overall/summary），
        或 None（评分失败时）
    """
    # agent 执行报错时直接返回低分
    if answer.startswith("ERROR:"):
        return {dim: {"score": 1, "reason": "Agent 执行报错"} for dim in SCORE_DIMENSIONS} | {
            "overall": 1.0,
            "summary": f"Agent 执行报错: {answer[:100]}",
        }

    client = _build_client()
    user_msg = JUDGE_USER_TEMPLATE.format(
        question=question,
        question_type=question_type,
        tool_outputs=tool_outputs,
        answer=answer,
        tool_call_count=tool_call_count,
        tool_call_summary=tool_call_summary or "无工具调用",
    )

    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
        )
        text = resp.choices[0].message.content or ""
    except Exception as e:
        logger.error("Judge LLM 调用失败: {}", e)
        return None

    parsed = _parse_judge_response(text)
    if parsed is None:
        logger.warning("Judge 响应解析失败 | raw={}", text[:500])
        return None

    validated = _validate_scores(parsed)
    if validated is None:
        logger.warning("Judge 评分格式校验失败 | parsed={}", parsed)
        return None

    validated["overall"] = _compute_overall(validated)
    if "summary" not in validated:
        validated["summary"] = ""

    return validated
