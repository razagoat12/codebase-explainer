"""
Five-agent pipeline powered by NVIDIA Nemotron (OpenAI-compatible endpoint),
with an automatic fallback chain — Kimi K2 → GLM 5.2 → DeepSeek V4, each
independently optional — tried in order once the primary NVIDIA key pool is
exhausted or rate-limited, or the primary call otherwise raises:
  1. Difficulty Assessor  → JSON
  2. Explainer            → markdown
  3. Planner              → markdown
  4. Diagram              → Mermaid
  5. Security Auditor     → JSON
"""
import itertools
import json
import logging
import threading
from dataclasses import dataclass, field

from openai import OpenAI, RateLimitError

from app.config import settings

logger = logging.getLogger(__name__)

# The SDK's default timeout is 10 minutes; with multiple agent calls per
# analysis, a slow/unresponsive upstream could leave a single analysis
# "processing" (and the fallback model never tried) for the better part of an
# hour. Cap each call so a stuck request fails fast and falls back instead.
_REQUEST_TIMEOUT_SECONDS = 60.0

# One client per configured NVIDIA key (settings.nvidia_api_key_pool is just
# [nvidia_api_key] unless NVIDIA_API_KEYS adds more). Each free key has its own
# per-minute rate limit, so pooling multiple keys multiplies how many analyses
# can run concurrently before anything 429s — see PLAN.md's key-pool section.
_client_pool = [
    OpenAI(base_url=settings.nvidia_base_url, api_key=key, timeout=_REQUEST_TIMEOUT_SECONDS)
    for key in settings.nvidia_api_key_pool
]
MODEL = settings.nvidia_model

_pool_lock = threading.Lock()
_pool_counter = itertools.count()


def _client_rotation() -> list[OpenAI]:
    """Pool clients starting from a different offset each call (round-robin),
    so load spreads across keys instead of always hammering the first one."""
    with _pool_lock:
        start = next(_pool_counter) % len(_client_pool)
    return _client_pool[start:] + _client_pool[:start]


@dataclass
class _FallbackBackend:
    client: OpenAI
    model: str
    top_p: float
    extra_body: dict | None = field(default=None)


def _fallback_backend(api_key: str, base_url: str, model: str, top_p: float, extra_body: dict | None = None):
    """Build a fallback backend only if its key is configured — keeps the
    primary path free of overhead when a given fallback isn't set up."""
    if not api_key:
        return None
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=_REQUEST_TIMEOUT_SECONDS)
    return _FallbackBackend(client=client, model=model, top_p=top_p, extra_body=extra_body)


# Tried in this order once the primary NVIDIA pool is exhausted/rate-limited.
# Each model expects its own reasoning-control param name (Nemotron uses
# "enable_thinking", DeepSeek uses "thinking", GLM takes neither) — preserved
# per-backend rather than assumed identical across providers.
_fallback_backends: list[_FallbackBackend] = [
    b
    for b in (
        _fallback_backend(settings.fallback_api_key, settings.fallback_base_url, settings.fallback_model, top_p=1.0),
        _fallback_backend(settings.glm_api_key, settings.glm_base_url, settings.glm_model, top_p=1.0),
        _fallback_backend(
            settings.deepseek_api_key,
            settings.deepseek_base_url,
            settings.deepseek_model,
            top_p=0.95,
            extra_body={"chat_template_kwargs": {"thinking": False}},
        ),
    )
    if b is not None
]

# Prompt budgets. Worst case (explainer): 16 files × 2500 chars ≈ 40K chars
# ≈ 10K tokens — well within Nemotron's context while keeping latency sane.
# Files are *ranked* before selection (see _select_files), so these budgets go
# to READMEs, entry points, and manifests instead of walk-order arbitrary files.
_MAX_ASSESSOR_FILES = 12
_MAX_EXPLAINER_FILES = 16
_MAX_FILE_CHARS = 2500

# File-ranking signals. READMEs and manifests tell the model what the project
# *is*; entry points anchor the control flow; plain source beats markup/styles.
_ENTRYPOINT_STEMS = {"main", "index", "app", "server", "cli", "__main__", "setup"}
_MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "requirements.txt", "go.mod",
    "cargo.toml", "gemfile", "composer.json", "pom.xml", "build.gradle",
    "dockerfile", "docker-compose.yml", "makefile",
}
_SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".kt",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".scala",
}

# Paths matching these substrings get a boost for the security auditor —
# auth flows, config, and DB access are where its findings live.
_SECURITY_KEYWORDS = (
    "auth", "login", "password", "token", "secret", "config", "settings",
    "env", "db", "database", "sql", "api", "crypto", "session",
)


def _score_file(f: dict, keywords: tuple[str, ...] | None = None) -> float:
    path = f["path"].lower()
    name = path.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0] if "." in name else name
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""

    score = 0.0
    if stem == "readme":
        score += 50
    if name in _MANIFEST_NAMES:
        score += 40
    if stem in _ENTRYPOINT_STEMS:
        score += 35
    if ext in _SOURCE_EXTENSIONS:
        score += 20
    if keywords and any(k in path for k in keywords):
        score += 25
    # Shallow files describe the project better than deeply nested ones
    score -= path.count("/") * 4
    # Tests restate the source; deprioritise (mildly — they still rank above
    # nothing when the budget allows)
    if "test" in path or "spec" in path:
        score -= 15
    # Substance bonus: bigger files carry more signal, capped so a giant
    # lockfile-ish blob can't outrank an entry point
    score += min(f.get("size") or len(f["content"]), 20000) / 2000
    return score


def _select_files(files: list[dict], max_files: int, keywords: tuple[str, ...] | None = None) -> list[dict]:
    """Pick the most informative files, highest score first (path breaks ties
    so selection is deterministic for identical content)."""
    ranked = sorted(files, key=lambda f: (-_score_file(f, keywords), f["path"]))
    return ranked[:max_files]


def _chat(system: str, user: str, temperature: float = 0.3, max_tokens: int = 4096) -> str:
    """
    Non-streaming chat call to Nemotron. `enable_thinking=False` keeps the
    response focused on the final answer (no separate reasoning stream to parse).

    On a 429 (rate limit), tries the next key in the pool before giving up on
    the primary model — a rate limit on one key says nothing about the model's
    quality, so it doesn't warrant dropping to a fallback model. Any other
    error (auth, network, timeout) goes straight to the fallback chain instead
    of burning through the whole pool for what's probably a systemic issue.

    Once the primary pool is exhausted ("queue is full") or a non-rate-limit
    error occurs, walks _fallback_backends in order (Kimi → GLM 5.2 →
    DeepSeek V4, each optional) and returns the first one that succeeds.
    Raises the last error only if every configured backend fails.
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    last_exc: Exception | None = None
    for pool_client in _client_rotation():
        try:
            resp = pool_client.chat.completions.create(
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
        except RateLimitError as exc:
            last_exc = exc
            logger.warning("NVIDIA key rate-limited (%s) — trying next key in pool", exc)
            continue
        except Exception as exc:
            last_exc = exc
            break

    for backend in _fallback_backends:
        try:
            logger.warning(
                "Primary model pool exhausted (%s) — trying fallback %s", last_exc, backend.model
            )
            kwargs = dict(
                model=backend.model,
                temperature=temperature,
                top_p=backend.top_p,
                max_tokens=max_tokens,
                messages=messages,
            )
            if backend.extra_body:
                kwargs["extra_body"] = backend.extra_body
            resp = backend.client.chat.completions.create(**kwargs)
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            last_exc = exc
            continue

    raise last_exc


def _format_files(
    files: list[dict],
    max_files: int,
    max_chars: int,
    keywords: tuple[str, ...] | None = None,
) -> str:
    parts = []
    for f in _select_files(files, max_files, keywords):
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


# Extension → language, used only for the degraded default when the model
# returns unparseable JSON twice. Rough is fine — it's a last resort.
_EXT_LANGUAGE = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JavaScript", ".tsx": "TypeScript", ".go": "Go", ".rs": "Rust",
    ".java": "Java", ".kt": "Kotlin", ".c": "C", ".cpp": "C++", ".cs": "C#",
    ".rb": "Ruby", ".php": "PHP", ".swift": "Swift", ".scala": "Scala",
}

_VALID_LEVELS = {"Beginner", "Intermediate", "Advanced"}


def _default_difficulty(language_counts: dict[str, int]) -> dict:
    """Degraded result when the model can't produce parseable JSON. The rest
    of the pipeline (Explainer, Planner) only needs *a* difficulty to proceed
    — better to continue with a neutral default than fail the whole analysis."""
    primary = "Unknown"
    if language_counts:
        top_ext = max(language_counts, key=language_counts.get)
        primary = _EXT_LANGUAGE.get(top_ext, top_ext.lstrip(".").upper() or "Unknown")
    return {
        "level": "Intermediate",
        "reason": "Automatic difficulty assessment was unavailable; defaulted to Intermediate.",
        "primary_language": primary,
        "frameworks": [],
    }


def assess_difficulty(ingestion_result: dict) -> dict:
    lang_stats = json.dumps(ingestion_result["stats"]["language_counts"], indent=2)
    sample_files = _format_files(ingestion_result["files"], _MAX_ASSESSOR_FILES, _MAX_FILE_CHARS)

    user_msg = f"""File tree:
{ingestion_result["file_tree"]}

Language stats:
{lang_stats}

File samples:
{sample_files}"""

    # The Explainer and Planner both depend on this result, so a malformed
    # response here must not sink the whole chain: retry once with a stricter
    # instruction, then fall back to a neutral default.
    for attempt, system in enumerate((
        _DIFFICULTY_SYSTEM,
        _DIFFICULTY_SYSTEM + "\nYour previous response was not valid JSON. "
        "Respond with the raw JSON object only — no prose, no fences.",
    )):
        raw = _chat(system, user_msg)
        try:
            result = json.loads(_extract_json(raw))
        except json.JSONDecodeError:
            logger.warning("Difficulty agent returned unparseable JSON (attempt %d)", attempt + 1)
            continue
        if not isinstance(result, dict):
            logger.warning("Difficulty agent returned non-object JSON (attempt %d)", attempt + 1)
            continue
        if result.get("level") not in _VALID_LEVELS:
            result["level"] = "Intermediate"
        result.setdefault("reason", "")
        result.setdefault("primary_language", "Unknown")
        result.setdefault("frameworks", [])
        return result

    return _default_difficulty(ingestion_result["stats"]["language_counts"])


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
    files = _format_files(
        ingestion_result["files"], _MAX_EXPLAINER_FILES, _MAX_FILE_CHARS,
        keywords=_SECURITY_KEYWORDS,
    )
    user_msg = f"""File tree:
{ingestion_result["file_tree"]}

Code to audit:
{files}"""

    raw = _chat(_SECURITY_SYSTEM, user_msg, temperature=0.1)
    try:
        return json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        return {"summary": "Security audit parse failed", "risk_level": "Low", "findings": []}


# The five agents above are orchestrated by app.analysis.routes, which runs the
# two independent ones (diagram, security) concurrently with the
# difficulty → explanation → plan chain and reports per-stage progress.
