"""深度研究 Pipeline 测试"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from deep_paper_qa.pipelines.research import clarify_node, plan_node, should_continue_clarify


class TestClarifyNode:
    """澄清节点测试"""

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.research.get_llm")
    async def test_increments_clarify_count(self, mock_get_llm: AsyncMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value.content = "问题已明确，可以制定研究计划。"
        mock_get_llm.return_value = mock_llm

        state = {
            "messages": [HumanMessage(content="调研 LLM Agent")],
            "plan": [],
            "current_step": 0,
            "findings": [],
            "clarify_count": 0,
        }
        result = await clarify_node(state)
        assert result["clarify_count"] == 1


class TestShouldContinueClarify:
    """澄清循环条件测试"""

    def test_stop_when_clear(self) -> None:
        state = {
            "messages": [AIMessage(content="问题已明确，可以制定研究计划。")],
            "clarify_count": 1,
        }
        assert should_continue_clarify(state) == "plan"

    def test_stop_when_max_reached(self) -> None:
        state = {
            "messages": [AIMessage(content="请问你想聚焦哪个方面？")],
            "clarify_count": 3,
        }
        assert should_continue_clarify(state) == "plan"

    def test_continue_when_unclear(self) -> None:
        state = {
            "messages": [AIMessage(content="请问你想聚焦哪个方面？")],
            "clarify_count": 1,
        }
        assert should_continue_clarify(state) == "ask_clarify"


class TestPlanNode:
    """研究计划节点测试"""

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.research.get_llm")
    async def test_generates_plan(self, mock_get_llm: AsyncMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value.content = json.dumps(
            [
                "子问题1: 使用 search_abstracts 检索 LLM Agent 框架",
                "子问题2: 使用 execute_sql 统计各年论文数",
                "子问题3: 使用 search_abstracts 检索多智能体协作",
            ]
        )
        mock_get_llm.return_value = mock_llm

        state = {
            "messages": [HumanMessage(content="调研 LLM Agent")],
            "plan": [],
            "current_step": 0,
            "findings": [],
            "clarify_count": 1,
        }
        result = await plan_node(state)
        assert len(result["plan"]) == 3
