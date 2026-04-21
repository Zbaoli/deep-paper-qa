"""SSE 事件构造"""

import json
from typing import Any

from sse_starlette.sse import ServerSentEvent


def sse(event: str, data: dict[str, Any] | None = None) -> ServerSentEvent:
    """构造 SSE 事件。data 为空时发空对象，前端 JSON.parse 不出错。"""
    return ServerSentEvent(event=event, data=json.dumps(data or {}, ensure_ascii=False))
