from __future__ import annotations

import hashlib
import json
import os
import random
import re
import threading
import time
from pathlib import Path

from .common import ROOT

_USAGE_LOCK = threading.Lock()  # lock global: vários clientes escrevem no mesmo usage.jsonl


def extract_json(text: str) -> dict:
    """Extrai o primeiro objeto JSON de uma resposta (tolera cercas ```json e texto em volta)."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < 0:
        raise ValueError("sem objeto JSON")
    return json.loads(t[i : j + 1])


class LLM:
    """Cliente por papel (diagnoser/generator/judge...), com cache em disco e retentativas.

    O cache guarda apenas respostas VÁLIDAS (JSON parseável quando json=True), chaveado por
    (modelo, temperatura, system, user, rep). Reexecutar o pipeline não gasta chamadas novas.
    """

    def __init__(self, role: str, cfg: dict):
        m = cfg["models"][role]
        p = cfg["providers"][m["provider"]]
        self.role, self.kind, self.name = role, p["kind"], m["name"]
        self.temperature = m.get("temperature", 0.0)
        self.max_tokens = m.get("max_tokens", 1200)
        self.json_mode = p.get("json_mode", False)
        self.extra_body = m.get("extra_body")  # ex.: {"reasoning": {"enabled": false}} (corta tokens de raciocínio)
        self.retries = cfg.get("runtime", {}).get("max_retries", 5)
        self.cache_path = ROOT / "cache" / f"{role}_{self.kind}.jsonl"
        self.usage_path = ROOT / "outputs" / "usage.jsonl"
        self._lock = threading.Lock()
        self._cache: dict[str, str] = {}
        if self.cache_path.exists():
            for line in self.cache_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    self._cache[r["k"]] = r["v"]
        self.client = None
        if self.kind == "openai_compat":
            from openai import OpenAI

            key = os.environ.get(p["api_key_env"])
            if not key:
                raise RuntimeError(
                    f"Variável de ambiente {p['api_key_env']} não definida (papel '{role}'). "
                    "Defina a chave ou rode com --mock."
                )
            self.client = OpenAI(base_url=p["base_url"], api_key=key, timeout=120, max_retries=0)

    def _key(self, system: str, user: str, rep: int) -> str:
        raw = json.dumps([self.kind, self.name, self.temperature, system, user, rep], ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _store(self, k: str, v: str) -> None:
        with self._lock:
            self._cache[k] = v
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"k": k, "v": v}, ensure_ascii=False) + "\n")

    def _log_usage(self, task: str, usage) -> None:
        if usage is None:
            return
        self.usage_path.parent.mkdir(parents=True, exist_ok=True)
        row = {"role": self.role, "model": self.name, "task": task,
               "in": getattr(usage, "prompt_tokens", 0), "out": getattr(usage, "completion_tokens", 0)}
        with _USAGE_LOCK, self.usage_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    def _raw(self, system: str, user: str, task: str, want_json: bool) -> str:
        if self.kind == "mock":
            from .mock import mock_reply

            return mock_reply(task, user)
        kwargs = dict(
            model=self.name,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if want_json and self.json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body
        last = None
        for a in range(self.retries):
            try:
                r = self.client.chat.completions.create(**kwargs)
                self._log_usage(task, r.usage)
                return r.choices[0].message.content or ""
            except Exception as e:  # noqa: BLE001  (rate limit, 5xx, timeout)
                last = e
                time.sleep(min(30, 2**a + random.random()))
        raise RuntimeError(f"falha após {self.retries} tentativas: {last}")

    def text(self, system: str, user: str, task: str, rep: int = 0) -> str:
        k = self._key(system, user, rep)
        if k in self._cache:
            return self._cache[k]
        v = self._raw(system, user, task, want_json=False).strip()
        if not v:
            raise ValueError("resposta vazia")
        self._store(k, v)
        return v

    def json(self, system: str, user: str, task: str, rep: int = 0) -> dict:
        k = self._key(system, user, rep)
        if k in self._cache:
            return extract_json(self._cache[k])
        last = None
        for _ in range(3):  # reamostra se o JSON vier quebrado
            v = self._raw(system, user, task, want_json=True)
            try:
                obj = extract_json(v)
            except Exception as e:  # noqa: BLE001
                last = e
                continue
            self._store(k, v)
            return obj
        raise ValueError(f"JSON inválido após 3 tentativas: {last}")


def make_llms(cfg: dict, roles: list[str]) -> dict[str, LLM]:
    return {r: LLM(r, cfg) for r in roles}
