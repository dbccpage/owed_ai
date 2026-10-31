import json

import httpx
import pytest

from anomalon_workbench.domain import Proposal, ProviderFailure
from anomalon_workbench.providers import (
    HTTPProvider,
    ProviderConfig,
    load_environment,
    redact,
    strict_output_schema,
)


def provider(handler, name="local", mode="json_prompt"):
    return HTTPProvider(
        ProviderConfig(
            name,
            "test-model",
            "http://localhost:1234/v1",
            mode,
            key="secret-test-key" if name != "local" else "",
        ),
        httpx.MockTransport(handler),
    )


def ask(p):
    return p.generate("system", "user", Proposal.model_json_schema(), 2048, 1)


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "authentication_failed"),
        (403, "authentication_failed"),
        (429, "rate_limited"),
        (422, "unsupported_request_or_model"),
        (500, "provider_http_error"),
    ],
)
def test_http_errors(status, code):
    with pytest.raises(ProviderFailure, match=code):
        ask(provider(lambda request: httpx.Response(status, json={"secret": "do not log"})))


def test_timeout_and_malformed():
    def timeout(request):
        raise httpx.ReadTimeout("sensitive details", request=request)

    with pytest.raises(ProviderFailure, match="provider_timeout"):
        ask(provider(timeout))
    with pytest.raises(ProviderFailure, match="malformed_provider_response"):
        ask(provider(lambda _: httpx.Response(200, json={"wrong": True})))


@pytest.mark.parametrize("name", ["local", "compatible", "openrouter"])
def test_chat_contract(name):
    def handler(request):
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["max_tokens"] == 2048
        assert body["response_format"]["json_schema"]["strict"]
        schema = body["response_format"]["json_schema"]["schema"]
        assert set(schema["required"]) == set(schema["properties"])
        assert "default" not in schema["properties"]["evidence_requests"]
        if name == "local":
            assert "authorization" not in request.headers
        else:
            assert request.headers["authorization"] == "Bearer secret-test-key"
        if name == "openrouter":
            assert body["provider"] == {"require_parameters": True, "allow_fallbacks": False}
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            },
        )

    assert ask(provider(handler, name, "json_schema")).input_tokens == 5


def test_strict_schema_preserves_host_contract_and_nested_requirements():
    original = Proposal.model_json_schema()
    before = json.dumps(original, sort_keys=True)
    projected = strict_output_schema(original)
    assert json.dumps(original, sort_keys=True) == before
    assert "evidence_requests" not in original["required"]
    assert set(projected["$defs"]["Repair"]["required"]) == {"edge_id", "difference"}
    proposal = Proposal.model_validate_json(
        '{"interpretation":"Unknown","verdict":"underdetermined",'
        '"evidence_requests":[],"repairs":[]}'
    )
    assert proposal.evidence_requests == ()
    with pytest.raises(ValueError):
        Proposal.model_validate_json(
            '{"interpretation":"Unknown","verdict":"underdetermined",'
            '"evidence_requests":[123],"repairs":[]}'
        )


def test_anthropic_contract_and_refusal():
    def handler(request):
        body = json.loads(request.content)
        assert request.headers["x-api-key"] == "secret-test-key"
        assert "output_config" in body
        assert "response_format" not in body
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "{}"}],
                "usage": {"input_tokens": 10, "output_tokens": 2},
                "stop_reason": "end_turn",
            },
        )

    assert ask(provider(handler, "anthropic", "json_schema")).output_tokens == 2
    with pytest.raises(ProviderFailure, match="refused_or_truncated"):
        ask(provider(lambda _: httpx.Response(200, json={"stop_reason": "refusal"}), "anthropic"))
    with pytest.raises(ProviderFailure, match="refused_or_truncated"):
        ask(
            provider(
                lambda _: httpx.Response(200, json={"choices": [{"message": {"refusal": "no"}}]})
            )
        )


def test_config_isolated_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-private-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "router-private-key")
    monkeypatch.delenv("WORKBENCH_BASE_URL", raising=False)
    assert ProviderConfig.from_env("anthropic", "x").key == "anthropic-private-key"
    local = ProviderConfig.from_env("local", "x")
    assert local.key == ""
    assert "key" not in local.public()
    dotenv = tmp_path / ".env"
    dotenv.write_text("ANTHROPIC_API_KEY=should-not-win\n")
    load_environment(dotenv)
    assert ProviderConfig.from_env("anthropic", "x").key == "anthropic-private-key"
    assert redact("anthropic-private-key router-private-key") == "[REDACTED] [REDACTED]"


def test_url_and_missing_model(monkeypatch):
    monkeypatch.delenv("WORKBENCH_MODEL", raising=False)
    with pytest.raises(ValueError):
        ProviderConfig.from_env("local")
    with pytest.raises(ValueError):
        ProviderConfig("local", "x", "http://example.com/v1").validate()
    with pytest.raises(ValueError):
        ProviderConfig("local", "x", "https://secret@host/v1").validate()
