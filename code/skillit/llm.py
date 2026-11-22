"""Minimal Gemini API client (REST) used by every prompt in the chain.

The API key is read from the GEMINI_API_KEY environment variable (or Streamlit secrets in the app).
Never hard-code a key in this repository.
"""
from __future__ import annotations

import os
import time

import requests

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
# Tried in order if the main model is not available on the free tier / quota is used up.
FALLBACK_MODELS = ["gemini-3.1-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"]


class LLMError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None, min_interval: float = 0.0):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self.api_key:
            raise LLMError("No Gemini API key. Set GEMINI_API_KEY (see README).")
        self.model = model or DEFAULT_MODEL
        self.min_interval = min_interval  # seconds between calls (free-tier rate limits)
        self._last_call = 0.0
        self.calls = 0

    def generate(self, system: str | None, user: str, temperature: float | None = None,
                 json_mode: bool = False, max_retries: int = 4) -> dict:
        """Return {'text', 'model', 'latency_s', 'usage'}."""
        body: dict = {"contents": [{"role": "user", "parts": [{"text": user}]}]}
        if system and system.strip().lower() != "none":
            body["systemInstruction"] = {"parts": [{"text": system}]}
        gen_cfg: dict = {}
        if temperature is not None:
            gen_cfg["temperature"] = temperature
        if json_mode:
            gen_cfg["responseMimeType"] = "application/json"
        if gen_cfg:
            body["generationConfig"] = gen_cfg

        models = [self.model] + [m for m in FALLBACK_MODELS if m != self.model]
        last_err = ""
        for model in models:
            for attempt in range(max_retries):
                wait = self.min_interval - (time.time() - self._last_call)
                if wait > 0:
                    time.sleep(wait)
                t0 = time.time()
                self._last_call = t0
                try:
                    resp = requests.post(API_URL.format(model=model),
                                         headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                                         json=body, timeout=120)
                except requests.RequestException as e:
                    last_err = str(e)
                    time.sleep(2 * (attempt + 1))
                    continue
                if resp.status_code == 200:
                    data = resp.json()
                    self.calls += 1
                    try:
                        parts = data["candidates"][0]["content"]["parts"]
                    except (KeyError, IndexError):
                        last_err = f"empty response: {str(data)[:300]}"
                        time.sleep(2)
                        continue
                    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                    if model != self.model:
                        self.model = model  # stick with the model that works
                    return {"text": text, "model": model, "latency_s": round(time.time() - t0, 2),
                            "usage": data.get("usageMetadata", {})}
                last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
                if resp.status_code in (404, 400) and "not found" in resp.text.lower():
                    break  # model name not available -> try next model
                if resp.status_code == 429 and "per day" in resp.text.lower():
                    break  # daily quota used -> try next model
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(min(60, 8 * (attempt + 1)))
                    continue
                raise LLMError(last_err)
        raise LLMError(f"All models failed. Last error: {last_err}")
