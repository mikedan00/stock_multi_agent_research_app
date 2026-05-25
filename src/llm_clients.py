from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import os
import requests


class LLMError(RuntimeError):
    pass


class BaseLLMClient:
    provider_name = "base"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_hint: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2200,
    ) -> str:
        raise NotImplementedError


class NoLLMClient(BaseLLMClient):
    provider_name = "none"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_hint: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2200,
    ) -> str:
        raise LLMError("No LLM provider configured. Using deterministic fallback templates.")


@dataclass
class AnthropicClient(BaseLLMClient):
    api_key: str
    model: str = "claude-sonnet-4-5"
    base_url: str = "https://api.anthropic.com/v1/messages"
    provider_name: str = "anthropic"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_hint: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2200,
    ) -> str:
        if not self.api_key:
            raise LLMError("ANTHROPIC_API_KEY is empty.")
        model = self.model or model_hint or "claude-sonnet-4-5"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        resp = requests.post(self.base_url, headers=headers, json=payload, timeout=120)
        if resp.status_code >= 400:
            raise LLMError(f"Anthropic API error {resp.status_code}: {resp.text[:1000]}")
        data = resp.json()
        parts = []
        for item in data.get("content", []):
            if item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts).strip()


@dataclass
class OpenAICompatibleClient(BaseLLMClient):
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4.1-mini"
    provider_name: str = "openai-compatible"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_hint: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2200,
    ) -> str:
        if not self.api_key:
            raise LLMError("OPENAI_COMPATIBLE_API_KEY is empty.")
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model or model_hint,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code >= 400:
            raise LLMError(f"OpenAI-compatible API error {resp.status_code}: {resp.text[:1000]}")
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise LLMError(f"Unexpected OpenAI-compatible response: {data}") from exc


@dataclass
class HuggingFaceClient(BaseLLMClient):
    """Hugging Face Inference Providers chat-completion client.

    It uses the HF router's OpenAI-compatible endpoint:
      https://router.huggingface.co/v1/chat/completions

    The `model` can be either a plain model id, e.g.
      google/gemma-4-26B-A4B-it
    or a provider-routed id, e.g.
      google/gemma-4-26B-A4B-it:novita
    """

    api_key: str
    base_url: str = "https://router.huggingface.co/v1"
    model: str = "google/gemma-4-26B-A4B-it"
    inference_provider: str = "auto"
    provider_name: str = "huggingface"

    def _routed_model(self, model_hint: Optional[str] = None) -> str:
        model = (self.model or model_hint or "google/gemma-4-26B-A4B-it").strip()
        route = (self.inference_provider or "auto").strip()
        # HF router accepts model-id:provider. Do not append when the user
        # already supplied an explicit provider suffix or selected auto.
        if route and route.lower() != "auto" and ":" not in model:
            return f"{model}:{route}"
        return model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_hint: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2200,
    ) -> str:
        if not self.api_key:
            raise LLMError("HF_TOKEN is empty.")
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._routed_model(model_hint),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=180)
        if resp.status_code >= 400:
            hint = ""
            if resp.status_code in {400, 404, 422}:
                hint = "\n확인: HF 모델 ID, provider suffix(:novita 등), Gemma 라이선스 동의, Inference Providers 권한을 확인하세요."
            raise LLMError(f"Hugging Face API error {resp.status_code}: {resp.text[:1000]}{hint}")
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise LLMError(f"Unexpected Hugging Face response: {data}") from exc


def build_llm_client(
    provider: str = "none",
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    hf_provider: str | None = None,
) -> BaseLLMClient:
    provider = (provider or "none").strip().lower()
    if provider in {"none", "no", "off"}:
        return NoLLMClient()
    if provider in {"huggingface", "hf", "hf-token"}:
        return HuggingFaceClient(
            api_key=api_key or os.getenv("HF_TOKEN", "") or os.getenv("HUGGINGFACEHUB_API_TOKEN", ""),
            base_url=base_url or os.getenv("HF_BASE_URL", "https://router.huggingface.co/v1"),
            model=model or os.getenv("HF_MODEL", "google/gemma-4-26B-A4B-it"),
            inference_provider=hf_provider or os.getenv("HF_INFERENCE_PROVIDER", "auto"),
        )
    if provider == "anthropic":
        return AnthropicClient(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""),
            model=model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
            base_url=base_url or os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1/messages"),
        )
    if provider in {"openai-compatible", "openai", "openrouter", "deepinfra", "novita"}:
        return OpenAICompatibleClient(
            api_key=api_key or os.getenv("OPENAI_COMPATIBLE_API_KEY", "") or os.getenv("OPENAI_API_KEY", ""),
            base_url=base_url or os.getenv("OPENAI_COMPATIBLE_BASE_URL", "https://api.openai.com/v1"),
            model=model or os.getenv("OPENAI_COMPATIBLE_MODEL", "gpt-4.1-mini"),
        )
    raise ValueError(f"Unsupported provider: {provider}")
