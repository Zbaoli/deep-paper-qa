"""generate_chart 工具测试"""

from unittest.mock import AsyncMock, patch

import plotly.graph_objects as go


class TestBuildFigure:
    """纯函数 _build_figure 单元测试（不经过 adispatch_custom_event）"""

    def test_bar_figure(self) -> None:
        from deep_paper_qa.tools.generate_chart import _build_figure

        fig = _build_figure("bar", {"x": ["2020", "2021"], "y": [10, 25]})
        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "bar"

    def test_pie_figure(self) -> None:
        from deep_paper_qa.tools.generate_chart import _build_figure

        fig = _build_figure("pie", {"labels": ["ACL", "NeurIPS"], "values": [100, 200]})
        assert fig.data[0].type == "pie"

    def test_mismatched_lengths_raises(self) -> None:
        """x/y 长度不一致应抛 ValueError"""
        import pytest
        from deep_paper_qa.tools.generate_chart import _build_figure

        with pytest.raises(ValueError, match="长度不一致"):
            _build_figure("bar", {"x": ["a"], "y": [1, 2]})


class TestGenerateChartTool:
    """tool 入口测试：mock adispatch_custom_event"""

    @patch("deep_paper_qa.tools.generate_chart.adispatch_custom_event", new_callable=AsyncMock)
    async def test_bar_chart_returns_str_and_dispatches_event(self, mock_dispatch) -> None:
        """生成柱状图：返回 str，通过 adispatch_custom_event 发 chart 事件"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "bar",
                "data": {"x": ["2020", "2021"], "y": [10, 25]},
                "title": "论文趋势",
            }
        )

        assert isinstance(result, str)
        assert "已生成" in result and "bar" in result
        # adispatch_custom_event 被调用一次，位置参数为 (name, data)
        assert mock_dispatch.await_count == 1
        args, _ = mock_dispatch.call_args
        assert args[0] == "chart"
        assert args[1]["type"] == "plotly"
        assert "figure" in args[1]

    @patch("deep_paper_qa.tools.generate_chart.adispatch_custom_event", new_callable=AsyncMock)
    async def test_invalid_chart_type_returns_error_str(self, mock_dispatch) -> None:
        """不支持的图表类型返回错误字符串，不调用 adispatch_custom_event"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "unknown",
                "data": {"x": [1], "y": [1]},
                "title": "test",
            }
        )

        assert isinstance(result, str)
        assert "不支持" in result
        assert mock_dispatch.await_count == 0

    @patch("deep_paper_qa.tools.generate_chart.adispatch_custom_event", new_callable=AsyncMock)
    async def test_mismatched_lengths_returns_error_str(self, mock_dispatch) -> None:
        """x/y 长度不一致返回错误字符串，不调用 adispatch_custom_event"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "bar",
                "data": {"x": ["2020", "2021"], "y": [10]},
                "title": "test",
            }
        )

        assert isinstance(result, str)
        assert "错误" in result or "长度" in result
        assert mock_dispatch.await_count == 0


class TestGenerateChartIntegration:
    """集成测试：验证 adispatch_custom_event 在 astream_events(v2) 下能被正确捕获"""

    async def test_chart_event_surfaces_via_astream_events(self) -> None:
        """工具在 StateGraph 中执行时，astream_events(v2) 能捕获到 chart 自定义事件"""
        from typing import TypedDict
        from langgraph.graph import END, START, StateGraph
        from deep_paper_qa.tools.generate_chart import generate_chart

        class State(TypedDict):
            result: str

        async def call_tool(state: State) -> dict:
            result = await generate_chart.ainvoke(
                {
                    "chart_type": "bar",
                    "data": {"x": ["2020", "2021"], "y": [10, 25]},
                    "title": "集成测试",
                }
            )
            return {"result": result}

        graph = StateGraph(State)
        graph.add_node("tool", call_tool)
        graph.add_edge(START, "tool")
        graph.add_edge("tool", END)
        compiled = graph.compile()

        custom_events = []
        async for event in compiled.astream_events({"result": ""}, version="v2"):
            if event.get("event") == "on_custom_event":
                custom_events.append(event)

        assert len(custom_events) == 1
        assert custom_events[0]["name"] == "chart"
        payload = custom_events[0]["data"]
        assert payload["type"] == "plotly"
        assert "figure" in payload
