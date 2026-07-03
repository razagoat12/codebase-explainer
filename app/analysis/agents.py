"""
Five-agent pipeline powered by NVIDIA Nemotron (OpenAI-compatible endpoint),
with an automatic fallback to a secondary model (Kimi K2 via the same NVIDIA
endpoint) if the primary call raises — timeout, rate limit, or outage:
  1. Difficulty Assessor  → JSON
  2. Explainer            → markdown
  3. Planner              → markdown
  4. Diagram              → Mermaid
  5. Security Auditor     → JSON
"""
import json
import logging

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

client = OpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key)
MODEL = settings.nvidia_model

# Fallback client is only constructed if a key is configured — keeps the
# primary path free of overhead when no fallback is set up.
_fallback_client = (
    OpenAI(base_url=settings.fallback_base_url, api_key=settings.fallback_api_key)
    if settings.fallback_api_key
    else None
)
FALLBACK_MODEL = settings.fallback_model

# Nemotron is a reasoning model — it can be slow. Keep prompts lean.
_MAX_ASSESSOR_FILES = 8
_MAX_EXPLAINER_FILES = 10
_MAX_FILE_CHARS = 400


def _chat(system: str, user: str, temperature: float = 0.3, max_tokens: int = 4096) -> str:
    """
    Non-streaming chat call to Nemotron. `enable_thinking=False` keeps the
    response focused on the final answer (no separate reasoning stream to parse).
    Falls back to a secondary model if the primary call raises and a fallback
    client is configured.
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            temperature=temperature,
            top_p=0.95,
            max_tokens=max_tokens,
            messages=messages,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False},
            },
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        if not _fallback_client:
            raise
        logger.warning(
            "Primary model call failed (%s) — falling back to %s", exc, FALLBACK_MODEL
        )
        resp = _fallback_client.chat.completions.create(
            model=FALLBACK_MODEL,
            temperature=temperature,
            top_p=1.0,
            max_tokens=max_tokens,
            messages=messages,
        )
        return (resp.choices[0].message.content or "").strip()


def _format_files(files: list[dict], max_files: int, max_chars: int) -> str:
    parts = []
    for f in files[:max_files]:
        snippet = f["content"][:max_chars]
        if len(f["content"]) > max_chars:
            snippet += "\n... (truncated)"
        parts.append(f"### {f['path']}\n```\n{snippet}\n```")
    return "\n\n".join(parts)


def _extract_json(raw: str) -> str:
    """Strip markdown fences and reasoning-preamble around a JSON blob."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"):
                return p[4:].strip()
            if p.startswith("{") or p.startswith("["):
                return p
    # Fallback: slice from first { to last }
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start : end + 1]
    return raw


# ── Agent 1: Difficulty ────────────────────────────────────────────────────────

_DIFFICULTY_SYSTEM = """You are a senior software engineer assessing codebase difficulty.
Return ONLY valid JSON (no markdown fences, no extra text) with exactly these keys:
{
  "level": "Beginner" | "Intermediate" | "Advanced",
  "reason": "<1-2 sentence explanation>",
  "primary_language": "<language name>",
  "frameworks": ["<framework1>", ...]
}"""


def assess_difficulty(ingestion_result: dict) -> dict:
    lang_stats = json.dumps(ingestion_result["stats"]["language_counts"], indent=2)
    sample_files = _format_files(ingestion_result["files"], _MAX_ASSESSOR_FILES, _MAX_FILE_CHARS)

    user_msg = f"""File tree:
{ingestion_result["file_tree"]}

Language stats:
{lang_stats}

File samples:
{sample_files}"""

    raw = _chat(_DIFFICULTY_SYSTEM, user_msg)
    return json.loads(_extract_json(raw))


# ── Agent 2: Explainer ─────────────────────────────────────────────────────────

_EXPLAINER_SYSTEM = """You are a patient, knowledgeable coding mentor.
Adapt style to difficulty level:
- Beginner: simple analogies, avoid jargon
- Intermediate: architecture patterns, data flow
- Advanced: design decisions, tradeoffs, scalability

Structure the response as markdown with clear headings."""


def explain_codebase(ingestion_result: dict, difficulty: dict) -> str:
    file_snippets = _format_files(ingestion_result["files"], _MAX_EXPLAINER_FILES, _MAX_FILE_CHARS)

    user_msg = f"""Difficulty: {difficulty["level"]} — {difficulty["reason"]}
Language: {difficulty["primary_language"]}
Frameworks: {", ".join(difficulty.get("frameworks", [])) or "none detected"}

File tree:
{ingestion_result["file_tree"]}

Key file snippets:
{file_snippets}

Write a plain-language explanation of this codebase for a {difficulty["level"]} developer."""

    return _chat(_EXPLAINER_SYSTEM, user_msg)


# ── Agent 3: Planner ───────────────────────────────────────────────────────────

_PLANNER_SYSTEM = """You are a pragmatic software architect. Produce a phased plan:
Phase 0 (MVP) → Phase 1 (core features) → Phase 2 (scale/security/polish).
Each phase must include: Goals, Key tasks, Security considerations.
Format as clean markdown."""


def generate_plan(ingestion_result: dict, explanation: str) -> str:
    user_msg = f"""Codebase explanation:
{explanation}

File tree:
{ingestion_result["file_tree"]}

Generate a phased plan with security considerations per phase."""

    return _chat(_PLANNER_SYSTEM, user_msg)


# ── Agent 4: Diagram ───────────────────────────────────────────────────────────

_DIAGRAM_SYSTEM = """You are a software architect. Output a Mermaid diagram of the main modules.
Use 'graph TD' syntax only. Max 12 nodes. Output ONLY raw Mermaid, no fences, no explanation."""


def generate_diagram(ingestion_result: dict) -> str:
    user_msg = f"""File tree:
{ingestion_result["file_tree"]}

Generate a Mermaid graph TD diagram of the main modules and relationships."""

    raw = _chat(_DIAGRAM_SYSTEM, user_msg, temperature=0.1)
    if "```" in raw:
        for part in raw.split("```"):
            p = part.strip()
            if p.startswith("mermaid"):
                return p[7:].strip()
            if p.startswith("graph"):
                return p
    return raw.strip()


# ── Agent 5: Security ──────────────────────────────────────────────────────────

_SECURITY_SYSTEM = """You are a security engineer. Return ONLY valid JSON (no fences):
{
  "summary": "<1-2 sentence overall security posture>",
  "risk_level": "Low" | "Medium" | "High" | "Critical",
  "findings": [
    {"severity": "low|medium|high|critical", "category": "secret|injection|exposed_env|weak_auth|other",
     "file": "<path>", "issue": "<what's wrong>", "fix": "<how to fix>"}
  ]
}
Look for: hardcoded secrets, SQL injection, exposed env vars in client code, weak password rules,
missing auth checks, unsafe deserialisation, command injection. If nothing is found, return empty
findings and risk_level "Low"."""


def audit_security(ingestion_result: dict) -> dict:
    files = _format_files(ingestion_result["files"], _MAX_EXPLAINER_FILES, _MAX_FILE_CHARS)
    user_msg = f"""File tree:
{ingestion_result["file_tree"]}

Code to audit:
{files}"""

    raw = _chat(_SECURITY_SYSTEM, user_msg, temperature=0.1)
    try:
        return json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        return {"summary": "Security audit parse failed", "risk_level": "Low", "findings": []}


# ── Orchestrator ───────────────────────────────────────────────────────────────

def run_pipeline(ingestion_result: dict) -> dict:
    difficulty = assess_difficulty(ingestion_result)
    explanation = explain_codebase(ingestion_result, difficulty)
    plan = generate_plan(ingestion_result, explanation)
    diagram = generate_diagram(ingestion_result)
    security = audit_security(ingestion_result)
    return {
        "difficulty": difficulty,
        "explanation": explanation,
        "plan": plan,
        "diagram": diagram,
        "security": security,
    }
