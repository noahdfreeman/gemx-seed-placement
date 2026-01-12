# LLM Integration for GEMx Recommendation Explanations

## Overview

This document outlines a lightweight Large Language Model (LLM) integration for GEMx to generate:

1. **Field-level reasons** — for each recommended hybrid/variety, generate a concise **1–2 sentence** reason describing why it fits the field.
2. **Farm-level summary** — when multiple fields are selected, generate a **2–4 sentence** summary describing why the recommended products were selected across the farm.

This integration is intentionally:

- **Provider-agnostic** (OpenAI-compatible API or local Ollama)
- **Safe-by-default** (LLM optional; deterministic fallback if disabled/misconfigured)
- **Structured** (LLM receives structured context and must return JSON)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                               GEMx                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────────┐ │
│  │ Scoring     │───▶│ Structured      │───▶│ LLM Provider         │ │
│  │ Engine      │    │ Context         │    │ (OpenAI / Ollama)    │ │
│  └─────────────┘    └─────────────────┘    └──────────┬───────────┘ │
│                                                       │             │
│  ┌─────────────────────┐                              │             │
│  │ Deterministic        │◀─────────────────────────────┘             │
│  │ fallback template    │                                            │
│  └─────────────────────┘                                            │
│                                                       │             │
│                     ┌─────────────────────┐           │             │
│                     │ UI / Report output  │◀──────────┘             │
│                     └─────────────────────┘                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Where This Lives in GEMX

- `GEMX/gemx_llm.py`
  - Provider interface + provider implementations
  - Prompt templates (system + structured user payload)
  - JSON parsing + guardrails
  - Deterministic fallback generation

- `GEMX/app.py`
  - Multi-field selection UI
  - Calls into `gemx_llm.generate_field_reasons()` per field
  - Calls into `gemx_llm.generate_farm_summary()` when multiple fields are selected

---

## Inputs and Outputs

### Field-level reasons

**Input (structured payload):**

- Field metadata: name/county/state/acres
- Environment: AWC, pH, soil texture, drainage, GDD, precip, heat stress
- Disease risk: the app’s 1–9 disease risk values
- Management: previous crop, tillage, herbicide program, fungicide
- Recommendation list:
  - product id (brand + name)
  - maturity (RM or MG)
  - score
  - rule-based strengths + watch-outs from the scoring logic
  - population
  - herbicide traits, technology

**Required output (JSON):**

```json
{
  "reasons": [
    {"id": "<recommendation id>", "reason": "<1-2 sentences>"}
  ]
}
```

### Farm-level summary

**Input (structured payload):**

- Crop
- Fields list with:
  - `field_name`
  - `county`, `state`
  - `top_product` (brand + name)

**Required output (JSON):**

```json
{
  "farm_summary": "<2-4 sentences>"
}
```

---

## Guardrails

The integration enforces these guardrails:

- Output must be valid JSON (JSON mode requested when supported)
- If JSON parsing fails or provider errors:
  - Fall back to deterministic template text
- Sentence limits:
  - Field reasons clipped to **<= 2 sentences**
  - Farm summary clipped to **<= 4 sentences**

LLM guidance:

- Use only provided context
- Do not invent yield/performance claims
- Avoid marketing language

---

## Configuration

Configuration is environment-variable driven.

### Enable / Disable

- `GEMX_LLM_ENABLED`
  - `true|false`
  - Default: `false`

### Provider

- `GEMX_LLM_PROVIDER`
  - `none` (default)
  - `openai` (OpenAI-compatible `/v1/chat/completions`)
  - `ollama` (local)

### Models

- `GEMX_LLM_MODEL`
  - Default: `gpt-4o-mini`
  - For Ollama, set to your local model name (e.g., `llama3.1:8b`)

### OpenAI-compatible

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` (optional)
  - Default: `https://api.openai.com`
  - Useful for Azure OpenAI or other compatible endpoints

### Ollama

- `OLLAMA_BASE_URL` (optional)
  - Default: `http://localhost:11434`

---

## Deterministic Fallback Behavior

When the LLM is disabled or unavailable, GEMx produces deterministic text from the existing rule-based explanations/warnings:

- If strengths exist:
  - `Selected because <top strengths>.` plus an optional watch-out.
- If only warnings exist:
  - Generic fit sentence + top warning.
- If neither exist:
  - Generic fit sentence based on maturity/trait match.

This ensures:

- The UI always shows reasons
- No external dependencies are required

---

## Example Usage

In the app, the per-recommendation reason is displayed at the top of each product expander.

For multi-field selection, the farm summary is displayed above the field tabs.

---

## Notes / Next Enhancements

Potential next steps:

- Add caching keyed by `(field_id, crop, management_hash, product_id)` to reduce LLM calls
- Add provider selection UI (OpenAI vs Ollama) and model selection UI
- Add JSON schema validation (Pydantic) around the LLM outputs
- Add per-field summary (in addition to per-product reasons) if desired
