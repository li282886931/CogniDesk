from __future__ import annotations

import os
import re
from typing import Any, Optional

import httpx


class LocalLlamaClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self.base_url = (base_url or os.getenv("LLAMA_SERVER_URL", "http://127.0.0.1:8080")).rstrip("/")
        self.model = model or os.getenv("LLAMA_MODEL", "gemma-4-e4b-it-qat-ud-q4")
        self.timeout = timeout or float(os.getenv("LLAMA_TIMEOUT_SECONDS", "30"))
        self.transport = transport

    def answer(self, question: str, context: str) -> Optional[str]:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是企业客服助手。只能根据提供的已发布知识回答。"
                        "如果知识不足，明确说无法确认并建议转人工。"
                        "不要输出思考过程，不要编造日期、价格、订单号或技术参数。"
                    ),
                },
                {"role": "user", "content": f"已发布知识：{context}\n客户问题：{question}"},
            ],
            "temperature": 0,
            "max_tokens": 256,
            "stream": False,
        }
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                result = client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )
                result.raise_for_status()
                content = result.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            return None
        cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE).strip()
        return cleaned or None
