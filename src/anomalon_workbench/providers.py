"""Small explicit HTTP adapters. Credentials never enter public configuration."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv
from pydantic import JsonValue

from .domain import ModelReply, ProviderFailure, canonical

ProviderName = Literal["anthropic", "openrouter", "compatible", "local"]


def load_environment(path: Path = Path(".env")) -> None:
    load_dotenv(path, override=False)


def redact(text: str) -> str:
    for name, value in os.environ.items():
        if any(s in name.upper() for s in ("API_KEY", "TOKEN", "SECRET")) and len(value) >= 8:
            text = text.replace(value, "[REDACTED]")
    return re.sub(r"\bsk-[A-Za-z0-9_-]{12,}", "[REDACTED]", text)


def strict_output_schema(schema: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Require explicit fields for strict chat endpoints; host validation stays unchanged.

    Our optional proposal collections must be emitted as empty arrays, not omitted.
    Return a new schema so adapting transport never mutates the host contract.
    """
    def visit(value: JsonValue) -> JsonValue:
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: visit(item) for key, item in value.items() if key != "default"}
        properties = result.get("properties")
        if isinstance(properties, dict):
            result["required"] = list(properties)
            result["additionalProperties"] = False
        return result

    return cast(dict[str, JsonValue], visit(schema))


@dataclass(frozen=True)
class ProviderConfig:
    provider: ProviderName
    model: str
    base_url: str
    output_mode: Literal["json_prompt", "json_schema"] = "json_prompt"
    key_env: str = "COMPATIBLE_API_KEY"
    key: str = field(default="", repr=False, compare=False)

    @classmethod
    def from_env(cls, provider: str | None = None, model: str | None = None) -> ProviderConfig:
        name = provider or os.getenv("WORKBENCH_PROVIDER", "openrouter")
        if name not in ("anthropic", "openrouter", "compatible", "local"):
            raise ValueError("unsupported_provider")
        selected = model or os.getenv("WORKBENCH_MODEL") or ""
        if not selected.strip():
            raise ValueError("An explicit WORKBENCH_MODEL or --model is required")
        key_env = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "compatible": os.getenv("WORKBENCH_KEY_ENV", "COMPATIBLE_API_KEY"),
            "local": "LOCAL_API_KEY",
        }[name]
        defaults = {
            "anthropic": "https://api.anthropic.com/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "compatible": "https://api.openai.com/v1",
            "local": "http://localhost:11434/v1",
        }
        mode = os.getenv("WORKBENCH_OUTPUT_MODE", "json_prompt")
        if mode not in ("json_prompt", "json_schema"):
            raise ValueError("unsupported_output_mode")
        result = cls(
            cast(ProviderName, name),
            selected,
            os.getenv("WORKBENCH_BASE_URL") or defaults[name],
            cast(Literal["json_prompt", "json_schema"], mode),
            key_env,
            os.getenv(key_env, ""),
        )
        result.validate()
        return result

    def validate(self) -> None:
        url = urlsplit(self.base_url)
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("base_url_must_not_contain_credentials_query_or_fragment")
        if url.scheme != "https" and not (
            url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1", "::1")
        ):
            raise ValueError("HTTPS_required_except_loopback")
        if self.provider != "local" and not self.key:
            raise ValueError(f"Missing {self.key_env}")
        if not self.model.strip():
            raise ValueError("model_required")

    def public(self) -> dict[str, JsonValue]:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "output_mode": self.output_mode,
            "key_env": self.key_env,
        }

    @classmethod
    def restore(cls, data: dict[str, JsonValue]) -> ProviderConfig:
        key_env = str(data["key_env"])
        result = cls(
            cast(ProviderName, data["provider"]),
            str(data["model"]),
            str(data["base_url"]),
            cast(Literal["json_prompt", "json_schema"], data["output_mode"]),
            key_env,
            os.getenv(key_env, ""),
        )
        result.validate()
        return result


class HTTPProvider:
    def __init__(self, config: ProviderConfig, transport: httpx.BaseTransport | None = None):
        self.config = config
        self.transport = transport

    def generate(
        self, system: str, user: str, schema: dict[str, JsonValue], max_tokens: int, timeout: float
    ) -> ModelReply:
        config = self.config
        system += (
            "\nReturn only JSON, without Markdown or code fences, matching this schema: "
            + canonical(schema)
        )
        headers = {"Content-Type": "application/json"}
        payload: dict[str, object] = {"model": config.model, "max_tokens": max_tokens}
        if config.provider == "anthropic":
            headers.update({"x-api-key": config.key, "anthropic-version": "2023-06-01"})
            payload.update({"system": system, "messages": [{"role": "user", "content": user}]})
            if config.output_mode == "json_schema":
                payload["output_config"] = {"format": {"type": "json_schema", "schema": schema}}
            endpoint = "/messages"
        else:
            if config.key:
                headers["Authorization"] = "Bearer " + config.key
            payload["messages"] = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
            if config.output_mode == "json_schema":
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "proposal",
                        "strict": True,
                        "schema": strict_output_schema(schema),
                    },
                }
                if config.provider == "openrouter":
                    payload["provider"] = {"require_parameters": True, "allow_fallbacks": False}
            elif config.provider == "openrouter":
                payload["provider"] = {"allow_fallbacks": False}
            endpoint = "/chat/completions"
        try:
            with httpx.Client(
                transport=self.transport, timeout=timeout, follow_redirects=False
            ) as client:
                response = client.post(
                    config.base_url.rstrip("/") + endpoint, headers=headers, json=payload
                )
            if response.status_code in (401, 403):
                raise ProviderFailure("authentication_failed")
            if response.status_code == 429:
                raise ProviderFailure("rate_limited")
            if response.status_code in (400, 404, 422):
                raise ProviderFailure("unsupported_request_or_model")
            if not response.is_success:
                raise ProviderFailure("provider_http_error")
            body = response.json()
            usage = body.get("usage", {})
            if config.provider == "anthropic":
                if body.get("stop_reason") in ("refusal", "max_tokens"):
                    raise ProviderFailure("refused_or_truncated")
                content = "".join(x["text"] for x in body["content"] if x.get("type") == "text")
                in_tokens, out_tokens = usage.get("input_tokens"), usage.get("output_tokens")
            else:
                choice = body["choices"][0]
                if choice["message"].get("refusal") or choice.get("finish_reason") in (
                    "length",
                    "content_filter",
                ):
                    raise ProviderFailure("refused_or_truncated")
                content = choice["message"]["content"]
                in_tokens, out_tokens = usage.get("prompt_tokens"), usage.get("completion_tokens")
            if not isinstance(content, str) or not content.strip():
                raise ProviderFailure("empty_response")
            cost = usage.get("cost")
            return ModelReply(
                content=redact(content),
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                cost=float(cost) if isinstance(cost, (float, int)) else None,
            )
        except httpx.TimeoutException:
            raise ProviderFailure("provider_timeout") from None
        except httpx.HTTPError:
            raise ProviderFailure("provider_connection_failed") from None
        except (ValueError, TypeError, KeyError, IndexError):
            raise ProviderFailure("malformed_provider_response") from None
