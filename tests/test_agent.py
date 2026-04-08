"""主图构建测试"""


class TestBuildGraph:
    """主图构建测试"""

    def test_graph_builds_successfully(self) -> None:
        """主图能正常构建"""
        from deep_paper_qa.agent import build_graph

        graph, checkpointer = build_graph()
        assert graph is not None
        assert checkpointer is not None

    def test_graph_has_correct_structure(self) -> None:
        """主图应包含正确的图结构"""
        from deep_paper_qa.agent import build_graph

        graph, _ = build_graph()
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")


class TestModels:
    """数据模型测试"""

    def test_paper_record_creation(self) -> None:
        from deep_paper_qa.models import PaperRecord

        paper = PaperRecord(
            id="arxiv:2312.07559",
            title="Test Paper",
            year=2025,
            authors=["Author A", "Author B"],
            directions=["RAG", "NLP"],
        )
        assert paper.id == "arxiv:2312.07559"
        assert len(paper.authors) == 2
        assert paper.citations == 0

    def test_search_result_creation(self) -> None:
        from deep_paper_qa.models import SearchChunk, SearchResult

        result = SearchResult(
            query="RAG methods",
            chunks=[
                SearchChunk(
                    paper_id="arxiv:2312.10997",
                    paper_title="RAG Survey",
                    content="Retrieval augmented generation...",
                    score=0.95,
                )
            ],
        )
        assert len(result.chunks) == 1
        assert result.chunks[0].score == 0.95
