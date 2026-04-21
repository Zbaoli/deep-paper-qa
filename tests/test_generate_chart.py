"""generate_chart 工具测试"""

from unittest.mock import MagicMock, patch

import plotly.graph_objects as go


class TestBuildFigure:
    """纯函数 _build_figure 单元测试（不经过 get_stream_writer）"""

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
    """tool 入口测试：mock get_stream_writer"""

    @patch("deep_paper_qa.tools.generate_chart.get_stream_writer")
    async def test_bar_chart_returns_str_and_writes_event(self, mock_writer_factory) -> None:
        """生成柱状图：返回 str，通过 writer 发 chart 事件"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        writer = MagicMock()
        mock_writer_factory.return_value = writer

        result = await generate_chart.ainvoke(
            {
                "chart_type": "bar",
                "data": {"x": ["2020", "2021"], "y": [10, 25]},
                "title": "论文趋势",
            }
        )

        assert isinstance(result, str)
        assert "已生成" in result and "bar" in result
        # writer 被调用一次，payload 结构符合约定
        assert writer.call_count == 1
        (payload,), _ = writer.call_args
        assert payload["event"] == "chart"
        assert payload["data"]["type"] == "plotly"
        assert "figure" in payload["data"]

    @patch("deep_paper_qa.tools.generate_chart.get_stream_writer")
    async def test_invalid_chart_type_returns_error_str(self, mock_writer_factory) -> None:
        """不支持的图表类型返回错误字符串，不调用 writer"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        writer = MagicMock()
        mock_writer_factory.return_value = writer

        result = await generate_chart.ainvoke(
            {
                "chart_type": "unknown",
                "data": {"x": [1], "y": [1]},
                "title": "test",
            }
        )

        assert isinstance(result, str)
        assert "不支持" in result
        assert writer.call_count == 0

    @patch("deep_paper_qa.tools.generate_chart.get_stream_writer")
    async def test_mismatched_lengths_returns_error_str(self, mock_writer_factory) -> None:
        """x/y 长度不一致返回错误字符串，不调用 writer"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        writer = MagicMock()
        mock_writer_factory.return_value = writer

        result = await generate_chart.ainvoke(
            {
                "chart_type": "bar",
                "data": {"x": ["2020", "2021"], "y": [10]},
                "title": "test",
            }
        )

        assert isinstance(result, str)
        assert "错误" in result or "长度" in result
        assert writer.call_count == 0
