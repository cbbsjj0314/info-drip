import asyncio
import json

from app.main import app


def test_health_endpoint_returns_ok() -> None:
    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/health",
        "raw_path": b"/health",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    asyncio.run(app(scope, receive, send))

    response_start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    response_body = next(
        message for message in messages if message["type"] == "http.response.body"
    )

    assert response_start["status"] == 200
    assert json.loads(response_body["body"]) == {"status": "ok"}
