import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional, Protocol


class BaseLLMProvider(Protocol):
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 300,
        json_mode: bool = False,
    ) -> str: ...


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    openai_api_key: Optional[str]
    openai_base_url: str
    ollama_base_url: str
    enabled: bool


class OpenAIProvider:
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 300,
        json_mode: bool = False,
    ) -> str:
        url = f"{self.base_url}/v1/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
            raise RuntimeError(f"OpenAI request failed ({e.code}): {detail}") from e
        except Exception as e:
            raise RuntimeError(f"OpenAI request failed: {e}") from e

        data = json.loads(body)
        return data["choices"][0]["message"]["content"]


class OllamaProvider:
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 300,
        json_mode: bool = False,
    ) -> str:
        url = f"{self.base_url}/api/generate"
        prompt = f"{system_prompt}\n\n{user_prompt}"
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            payload["format"] = "json"

        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
            raise RuntimeError(f"Ollama request failed ({e.code}): {detail}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e

        data = json.loads(body)
        return data.get("response", "")


def load_llm_config() -> LLMConfig:
    secrets: dict[str, Any] = {}
    try:
        import streamlit as st  # type: ignore

        secrets = dict(getattr(st, "secrets", {}) or {})
    except Exception:
        secrets = {}

    def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
        env_val = os.getenv(key)
        if env_val is not None:
            return env_val
        if key in secrets:
            val = secrets.get(key)
            return str(val) if val is not None else None
        return default

    provider = (get_setting("GEMX_LLM_PROVIDER", "none") or "none").strip().lower()
    enabled_raw = (get_setting("GEMX_LLM_ENABLED", "false") or "false").strip().lower()
    enabled = enabled_raw in {"1", "true", "yes", "y"}

    return LLMConfig(
        provider=provider,
        model=(get_setting("GEMX_LLM_MODEL", "gpt-4o-mini") or "gpt-4o-mini").strip(),
        openai_api_key=get_setting("OPENAI_API_KEY"),
        openai_base_url=(get_setting("OPENAI_BASE_URL", "https://api.openai.com") or "https://api.openai.com").strip(),
        ollama_base_url=(get_setting("OLLAMA_BASE_URL", "http://localhost:11434") or "http://localhost:11434").strip(),
        enabled=enabled,
    )


def get_llm_provider(config: Optional[LLMConfig] = None) -> Optional[BaseLLMProvider]:
    cfg = config or load_llm_config()
    if not cfg.enabled or cfg.provider in {"none", "disabled", "off"}:
        return None

    if cfg.provider in {"openai", "azure_openai", "openai_compatible"}:
        if not cfg.openai_api_key:
            return None
        return OpenAIProvider(api_key=cfg.openai_api_key, model=cfg.model, base_url=cfg.openai_base_url)

    if cfg.provider in {"ollama", "local"}:
        return OllamaProvider(model=cfg.model, base_url=cfg.ollama_base_url)

    return None


def _clip_sentences(text: str, max_sentences: int) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return ""

    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    parts = [p.strip() for p in parts if p.strip()]
    clipped = " ".join(parts[:max_sentences])
    return clipped


def _fallback_reason(rule_explanations: list[str], rule_warnings: list[str], *, crop: str) -> str:
    expl = [e.strip() for e in (rule_explanations or []) if e and e.strip()]
    warn = [w.strip() for w in (rule_warnings or []) if w and w.strip()]

    if expl:
        base = expl[:2]
        if warn:
            sentence = f"Selected because {', '.join(base)}. Watch: {warn[0]}."
        else:
            sentence = f"Selected because {', '.join(base)}."
        return _clip_sentences(sentence, 2)

    if warn:
        return _clip_sentences(f"Selected as a good overall fit for this {crop.lower()} field. Watch: {warn[0]}.", 2)

    return _clip_sentences(f"Selected as a strong overall fit for this {crop.lower()} field based on maturity and trait match.", 2)


def generate_field_reasons(
    *,
    field: dict[str, Any],
    crop: str,
    management: dict[str, Any],
    ranked_results: list[dict[str, Any]],
    provider: Optional[BaseLLMProvider],
) -> dict[str, str]:
    reasons: dict[str, str] = {}

    if not ranked_results:
        return reasons

    if provider is None:
        for item in ranked_results:
            product = item["product"]
            result = item["result"]
            rec_id = f"{product.get('brand', '')} {product.get('name', '')}".strip()
            reasons[rec_id] = _fallback_reason(
                result.get("explanations", []),
                result.get("warnings", []),
                crop=crop,
            )
        return reasons

    system_prompt = (
        "You are an agronomy seed placement assistant. "
        "Write a concise 1-2 sentence reason for why each recommended hybrid/variety fits the specific field. "
        "Use only the provided context. Do not invent performance claims. "
        "Avoid brand marketing language. Keep it practical. "
        "Return JSON only."
    )

    payload = {
        "task": "field_recommendation_reasons",
        "constraints": {"reason_sentences_max": 2},
        "field": {
            "name": field.get("name"),
            "county": field.get("county"),
            "state": field.get("state"),
            "acres": field.get("acres"),
            "environment": field.get("environment", {}),
            "disease_risk": field.get("disease_risk", {}),
            "crop": crop,
            "management": management,
        },
        "recommendations": [
            {
                "id": f"{item['product'].get('brand', '')} {item['product'].get('name', '')}".strip(),
                "brand": item["product"].get("brand"),
                "name": item["product"].get("name"),
                "maturity": item["product"].get("relative_maturity")
                if crop == "Corn"
                else item["product"].get("maturity_group"),
                "score": item["result"].get("score"),
                "rule_strengths": item["result"].get("explanations", []),
                "rule_watch_outs": item["result"].get("warnings", []),
                "population": item["result"].get("population"),
                "technology": item["product"].get("technology", []),
                "herbicide_traits": item["product"].get("herbicide_traits", []),
            }
            for item in ranked_results
        ],
        "required_output_json": {
            "reasons": [
                {
                    "id": "<recommendation id>",
                    "reason": "<1-2 sentences>"
                }
            ]
        },
    }

    user_prompt = json.dumps(payload, indent=2)

    try:
        raw = provider.generate(system_prompt, user_prompt, temperature=0.2, max_tokens=600, json_mode=True)
        parsed = json.loads(raw)
        for item in parsed.get("reasons", []):
            rec_id = (item.get("id") or "").strip()
            reason = _clip_sentences(item.get("reason", ""), 2)
            if rec_id and reason:
                reasons[rec_id] = reason
    except Exception:
        for item in ranked_results:
            product = item["product"]
            result = item["result"]
            rec_id = f"{product.get('brand', '')} {product.get('name', '')}".strip()
            reasons[rec_id] = _fallback_reason(
                result.get("explanations", []),
                result.get("warnings", []),
                crop=crop,
            )

    for item in ranked_results:
        product = item["product"]
        result = item["result"]
        rec_id = f"{product.get('brand', '')} {product.get('name', '')}".strip()
        if rec_id not in reasons:
            reasons[rec_id] = _fallback_reason(
                result.get("explanations", []),
                result.get("warnings", []),
                crop=crop,
            )

    return reasons


def generate_farm_summary(
    *,
    crop: str,
    field_recommendations: list[dict[str, Any]],
    provider: Optional[BaseLLMProvider],
) -> str:
    if len(field_recommendations) <= 1:
        return ""

    if provider is None:
        top_products = []
        for fr in field_recommendations:
            if fr.get("top_product"):
                top_products.append(fr["top_product"])

        unique = []
        for p in top_products:
            if p not in unique:
                unique.append(p)

        if not unique:
            return _clip_sentences(
                f"Across the selected fields, the recommended {crop.lower()} products are driven primarily by maturity fit and the field-specific disease and stress profile.",
                4,
            )

        if len(unique) == 1:
            return _clip_sentences(
                f"Across the selected fields, {unique[0]} was the top fit for the farm. "
                f"The recommendation is consistent because the fields share similar maturity needs and the same main stress and disease pressures. "
                f"Use field-level notes to adjust population and management where soil and drainage differ.",
                4,
            )

        return _clip_sentences(
            f"Across the selected fields, the tool favored {', '.join(unique[:3])}{'...' if len(unique) > 3 else ''}. "
            f"Differences in soil water-holding, drainage, and disease pressure shifted the ranking by field, even under the same overall crop plan. "
            f"Use the per-field reasons to decide where to place each product and whether to adjust protection (e.g., fungicide) on higher-risk acres.",
            4,
        )

    system_prompt = (
        "You are an agronomy seed placement assistant. "
        "Write a concise 2-4 sentence farm-level summary explaining why the selected hybrids/varieties were chosen across multiple fields. "
        "Use only provided context and do not invent performance claims. "
        "Return JSON only."
    )

    payload = {
        "task": "farm_summary",
        "constraints": {"sentences_min": 2, "sentences_max": 4},
        "crop": crop,
        "fields": field_recommendations,
        "required_output_json": {"farm_summary": "<2-4 sentences>"},
    }

    try:
        raw = provider.generate(system_prompt, json.dumps(payload, indent=2), temperature=0.2, max_tokens=400, json_mode=True)
        parsed = json.loads(raw)
        return _clip_sentences(parsed.get("farm_summary", ""), 4)
    except Exception:
        return _clip_sentences(
            f"Across the selected fields, the recommended {crop.lower()} products are driven primarily by maturity fit and the field-specific disease and stress profile.",
            4,
        )
