"""路由分类测试"""

from deep_paper_qa.models import RouteCategory, RouterOutput


class TestRouterOutput:
    """路由输出模型测试"""

    def test_valid_category(self) -> None:
        output = RouterOutput(category=RouteCategory.GENERAL)
        assert output.category == RouteCategory.GENERAL

    def test_all_categories_exist(self) -> None:
        expected = {"reject", "general", "research", "reading", "compare", "trend"}
        actual = {c.value for c in RouteCategory}
        assert actual == expected
