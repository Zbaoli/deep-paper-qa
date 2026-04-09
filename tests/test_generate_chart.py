"""generate_chart 工具测试"""


class TestGenerateChart:
    """通用图表生成工具测试"""

    async def test_bar_chart(self) -> None:
        """生成柱状图：返回简短确认文本（content_and_artifact 格式）"""
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
        # content_and_artifact 格式：ainvoke 返回 content 字符串
        assert "已生成" in result
        assert "bar" in result

    async def test_line_chart(self) -> None:
        """生成折线图：返回简短确认文本"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "line",
                "data": {"x": ["2020", "2021", "2022"], "y": [10, 25, 40]},
                "title": "增长趋势",
            }
        )
        assert "已生成" in result

    async def test_pie_chart(self) -> None:
        """生成饼图：返回简短确认文本"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "pie",
                "data": {"labels": ["ACL", "NeurIPS", "ICLR"], "values": [100, 200, 150]},
                "title": "会议分布",
            }
        )
        assert "已生成" in result

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
        assert "不支持" in result or "错误" in result

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
        assert "长度" in result or "错误" in result
