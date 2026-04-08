"""generate_chart 工具测试"""

import json

import pytest


class TestGenerateChart:
    """通用图表生成工具测试"""

    async def test_bar_chart(self) -> None:
        """生成柱状图"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "bar",
                "data": {"x": ["2020", "2021", "2022"], "y": [10, 25, 40]},
                "title": "论文数量趋势",
                "x_label": "年份",
                "y_label": "数量",
            }
        )
        assert "<!--plotly:" in result
        assert "-->" in result
        chart_json = result.split("<!--plotly:")[1].split("-->")[0]
        fig_data = json.loads(chart_json)
        assert "data" in fig_data
        assert "layout" in fig_data

    async def test_line_chart(self) -> None:
        """生成折线图"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "line",
                "data": {"x": ["2020", "2021", "2022"], "y": [10, 25, 40]},
                "title": "增长趋势",
            }
        )
        assert "<!--plotly:" in result

    async def test_pie_chart(self) -> None:
        """生成饼图"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "pie",
                "data": {"labels": ["ACL", "NeurIPS", "ICLR"], "values": [100, 200, 150]},
                "title": "会议分布",
            }
        )
        assert "<!--plotly:" in result

    async def test_invalid_chart_type(self) -> None:
        """不支持的图表类型返回错误信息"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "unknown",
                "data": {"x": [1], "y": [1]},
                "title": "test",
            }
        )
        assert "不支持" in result or "error" in result.lower()

    async def test_mismatched_data_lengths(self) -> None:
        """x/y 长度不一致返回错误信息"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "bar",
                "data": {"x": ["2020", "2021"], "y": [10]},
                "title": "test",
            }
        )
        assert "长度" in result or "mismatch" in result.lower() or "error" in result.lower()
