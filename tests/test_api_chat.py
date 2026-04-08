"""聊天 API 路由测试"""

from fastapi.testclient import TestClient

from deep_paper_qa.api import app


class TestHealthEndpoint:
    """健康检查测试"""

    def test_health(self) -> None:
        client = TestClient(app)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestReplyEndpoint:
    """POST /api/chat/{thread_id}/reply 测试"""

    def test_reply_no_pending(self) -> None:
        """没有等待中的问题时返回 404"""
        client = TestClient(app)
        resp = client.post(
            "/api/chat/nonexistent/reply",
            json={"reply": "继续"},
        )
        assert resp.status_code == 404
