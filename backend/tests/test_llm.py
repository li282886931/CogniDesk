import httpx

from app.llm import LocalLlamaClient


def test_llama_client_returns_answer_without_thinking_markup():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "<think>内部推理</think>物流会在承诺时效内更新。"}}
                ]
            },
        )

    client = LocalLlamaClient(
        base_url="http://llama.test",
        model="local-model",
        transport=httpx.MockTransport(handler),
    )

    assert client.answer("物流多久更新？", "已发布知识：物流服务规范。") == "物流会在承诺时效内更新。"


def test_llama_client_returns_none_when_server_is_unavailable():
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    client = LocalLlamaClient(
        base_url="http://llama.test",
        transport=httpx.MockTransport(handler),
        timeout=0.1,
    )

    assert client.answer("订单状态？", "没有可引用知识。") is None
