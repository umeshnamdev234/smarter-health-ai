"""Client for MedGemma served behind any OpenAI-compatible API
(Ollama, vLLM, Hugging Face TGI / Inference Endpoints, ...)."""
import json
from typing import AsyncIterator, Optional

import httpx

from .schemas import Message


class LLMUnavailable(Exception):
    """The model server could not be reached."""


class LLMError(Exception):
    """The model server returned an error."""


class MedGemmaClient:
    def __init__(self, base_url: str, model: str, api_key: str = "", timeout_s: float = 300.0):
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.model = model
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers=headers,
            timeout=httpx.Timeout(timeout_s, connect=5.0),
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    # ---------- helpers ----------
    @staticmethod
    def build_messages(system_prompt: str, messages: list[Message]) -> list[dict]:
        out: list[dict] = [{"role": "system", "content": system_prompt}]
        for m in messages:
            if m.images:
                parts: list[dict] = [{"type": "text", "text": m.content or ""}]
                parts += [
                    {"type": "image_url", "image_url": {"url": f"data:{im.mime_type};base64,{im.data}"}}
                    for im in m.images
                ]
                out.append({"role": m.role, "content": parts})
            else:
                out.append({"role": m.role, "content": m.content})
        return out

    def _payload(self, messages: list[dict], temperature: float, max_tokens: int, model: Optional[str], stream: bool, json_mode: bool = False) -> dict:
        p = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if stream:
            p["stream_options"] = {"include_usage": True}
        if json_mode:
            p["response_format"] = {"type": "json_object"}
        return p

    async def _request(self, method: str, path: str, **kw) -> dict:
        try:
            r = await self._http.request(method, path, **kw)
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise LLMUnavailable(f"Model server unreachable at {self._http.base_url}") from e
        except httpx.TimeoutException as e:
            raise LLMError("Model server timed out") from e
        if r.status_code >= 400:
            raise LLMError(f"Model server error {r.status_code}: {r.text[:300]}")
        return r.json()

    # ---------- public API ----------
    async def list_models(self) -> list[str]:
        data = await self._request("GET", "models")
        return [m["id"] for m in data.get("data", [])]

    async def chat(self, messages: list[dict], *, temperature: float, max_tokens: int, model: Optional[str] = None, json_mode: bool = False) -> dict:
        data = await self._request("POST", "chat/completions", json=self._payload(messages, temperature, max_tokens, model, False, json_mode))
        try:
            content = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as e:
            raise LLMError("Unexpected response from model server") from e
        return {"content": content, "model": data.get("model", model or self.model), "usage": data.get("usage")}

    async def stream(self, messages: list[dict], *, temperature: float, max_tokens: int, model: Optional[str] = None) -> AsyncIterator[dict]:
        """Yields {"delta": str} for text chunks and {"usage": dict} at the end (if the server reports it)."""
        payload = self._payload(messages, temperature, max_tokens, model, True)
        try:
            async with self._http.stream("POST", "chat/completions", json=payload) as r:
                if r.status_code >= 400:
                    body = (await r.aread()).decode(errors="replace")
                    raise LLMError(f"Model server error {r.status_code}: {body[:300]}")
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    if chunk.get("error"):
                        raise LLMError(str(chunk["error"]))
                    for choice in chunk.get("choices") or []:
                        delta = (choice.get("delta") or {}).get("content")
                        if delta:
                            yield {"delta": delta}
                    if chunk.get("usage"):
                        yield {"usage": chunk["usage"]}
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise LLMUnavailable(f"Model server unreachable at {self._http.base_url}") from e
        except httpx.TimeoutException as e:
            raise LLMError("Model server timed out") from e
