"""Exercises the real OpenAI / Anthropic / Gemini SDK clients against a local fake HTTP server.
Proves request building and response/usage parsing; does NOT prove behaviour against the live APIs."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.llm import LLMConfig, LLMRouter, ModelSpec
from app.llm.config import ProviderSettings

SEEN = []


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        SEEN.append((self.path, body))
        if "chat/completions" in self.path:
            out = {"id": "x", "object": "chat.completion", "created": 1, "model": "m",
                   "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "hi-openai"}}],
                   "usage": {"prompt_tokens": 11, "completion_tokens": 3, "total_tokens": 14}}
        elif "/messages" in self.path:
            out = {"id": "x", "type": "message", "role": "assistant", "model": "m", "stop_reason": "end_turn",
                   "content": [{"type": "text", "text": "hi-anthropic"}], "usage": {"input_tokens": 12, "output_tokens": 4}}
        else:
            out = {"candidates": [{"content": {"role": "model", "parts": [{"text": "hi-gemini"}]}, "finishReason": "STOP"}],
                   "usageMetadata": {"promptTokenCount": 13, "candidatesTokenCount": 5}}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.mark.parametrize("provider,env,expect,tokens", [
    ("openai", "OPENAI_API_KEY", "hi-openai", (11, 3)),
    ("anthropic", "ANTHROPIC_API_KEY", "hi-anthropic", (12, 4)),
    ("gemini", "GEMINI_API_KEY", "hi-gemini", (13, 5)),
])
async def test_sdk_roundtrip(server, monkeypatch, provider, env, expect, tokens):
    monkeypatch.setenv(env, "test-key")
    base = server + ("/v1" if provider == "openai" else "")
    cfg = LLMConfig(providers={provider: ProviderSettings(api_key_env=env, base_url=base)},
                    default=ModelSpec(provider=provider, model="some-model"))
    r = await LLMRouter(cfg).complete([{"role": "system", "content": "sys"}, {"role": "user", "content": "hello"}],
                                      max_tokens=50, temperature=0.1)
    assert r.text == expect and (r.input_tokens, r.output_tokens) == tokens and r.provider == provider
    path, body = SEEN[-1]
    if provider == "anthropic":
        assert body["system"] == "sys" and body["messages"] == [{"role": "user", "content": "hello"}]


async def test_missing_key_is_clear_error(monkeypatch):
    from app.llm import LLMError
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = LLMConfig(default=ModelSpec(provider="openai", model="m"))
    with pytest.raises(LLMError, match="Missing OPENAI_API_KEY"):
        await LLMRouter(cfg).complete([{"role": "user", "content": "x"}])
