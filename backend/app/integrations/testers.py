"""Endpoints de validação por provider — chamada barata pra confirmar credencial."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass

import httpx


@dataclass
class TestResult:
    ok: bool
    latency_ms: int
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _measure(fn, *args, **kwargs) -> TestResult:
    t0 = time.monotonic()
    try:
        return fn(*args, **kwargs, _t0=t0)
    except Exception as exc:
        return TestResult(
            ok=False,
            latency_ms=int((time.monotonic() - t0) * 1000),
            error=str(exc)[:200],
        )


def _result(ok: bool, t0: float, error: str | None = None) -> TestResult:
    return TestResult(
        ok=ok,
        latency_ms=int((time.monotonic() - t0) * 1000),
        error=error,
    )


def check_resend(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.get(
        "https://api.resend.com/domains",
        headers={"Authorization": f"Bearer {cfg['api_key']}"},
        timeout=10.0,
    )
    return _result(
        ok=r.status_code == 200,
        t0=t0,
        error=r.text[:200] if r.status_code != 200 else None,
    )


def check_telegram(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.get(
        f"https://api.telegram.org/bot{cfg['bot_token']}/getMe",
        timeout=10.0,
    )
    body = r.json() if r.status_code == 200 else {}
    return _result(
        ok=r.status_code == 200 and body.get("ok") is True,
        t0=t0,
        error=r.text[:200] if r.status_code != 200 else None,
    )


def check_apify(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.get(
        f"https://api.apify.com/v2/users/me?token={cfg['token']}",
        timeout=10.0,
    )
    return _result(
        ok=r.status_code == 200,
        t0=t0,
        error=r.text[:200] if r.status_code != 200 else None,
    )


def check_llm(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.post(
        f"{cfg['base_url']}/chat/completions",
        headers={
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": cfg["model"],
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        },
        timeout=15.0,
    )
    return _result(
        ok=r.status_code == 200,
        t0=t0,
        error=r.text[:200] if r.status_code != 200 else None,
    )


def check_hunter(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.get(
        f"https://api.hunter.io/v2/account?api_key={cfg['api_key']}",
        timeout=10.0,
    )
    return _result(
        ok=r.status_code == 200,
        t0=t0,
        error=r.text[:200] if r.status_code != 200 else None,
    )


def check_apollo(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.get(
        "https://api.apollo.io/v1/auth/health",
        headers={"X-Api-Key": cfg["api_key"]},
        timeout=10.0,
    )
    return _result(
        ok=r.status_code == 200,
        t0=t0,
        error=r.text[:200] if r.status_code != 200 else None,
    )


def check_evolution(cfg: dict, _t0: float | None = None) -> TestResult:
    """Health check de instância Evolution API.

    Considera ok=True apenas quando state == "open" (instância conectada
    ao WhatsApp). Demais estados (connecting/close) → ok=False com
    state no error pra UI exibir.
    """
    t0 = _t0 if _t0 is not None else time.monotonic()
    base_url = cfg["base_url"].rstrip("/")
    instance = cfg["instance"]
    api_key = cfg["api_key"]
    if hasattr(api_key, "get_secret_value"):
        api_key = api_key.get_secret_value()
    r = httpx.get(
        f"{base_url}/instance/connectionState/{instance}",
        headers={"apikey": api_key},
        timeout=10.0,
    )
    if r.status_code != 200:
        return _result(ok=False, t0=t0, error=r.text[:200])
    body = r.json() if r.text else {}
    state = (body.get("instance") or {}).get("state", "unknown")
    return _result(
        ok=state == "open",
        t0=t0,
        error=None if state == "open" else f"state={state}",
    )


def check_langsmith(cfg: dict, _t0: float | None = None) -> TestResult:
    t0 = _t0 if _t0 is not None else time.monotonic()
    r = httpx.get(
        "https://api.smith.langchain.com/info",
        headers={"x-api-key": cfg["api_key"]},
        timeout=10.0,
    )
    return _result(
        ok=r.status_code == 200,
        t0=t0,
        error=r.text[:200] if r.status_code != 200 else None,
    )


TESTERS: dict[str, callable] = {
    "resend": check_resend,
    "telegram": check_telegram,
    "apify": check_apify,
    "llm": check_llm,
    "hunter": check_hunter,
    "apollo": check_apollo,
    "evolution": check_evolution,
    "langsmith": check_langsmith,
}


def run_test(provider: str, cfg: dict) -> TestResult:
    fn = TESTERS.get(provider)
    if fn is None:
        return TestResult(ok=False, latency_ms=0, error=f"unknown provider: {provider}")
    return _measure(fn, cfg)
