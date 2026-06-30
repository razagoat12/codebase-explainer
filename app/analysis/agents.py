"""
Three-agent Groq pipeline (LLaMA 3.1 8B Instant):
  1. Difficulty Assessor  → returns structured JSON
  2. Explainer            → returns plain-language markdown explanation
  3. Planner              → returns phased plan markdown
"""
import json

from groq import Groq

from app.config import settings

MODEL = "llama-3.1-8b-instant"
client = Groq(api_key=settings.groq_api_key)

# Keep prompts token-efficient for free tier (20K TPM limit)
_MAX_ASSESSOR_FILES = 8
_MAX_EXPLAINER_FILES = 10
_MAX_FILE_CHARS = 400


def _chat(system: str, user: str, temperature: float = 0.3) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=temperature,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content.strip()


def _format_files(files: list[dict], max_files: int, max_chars: int) -> str:
    parts = []
    for f in files[:max_files]:
        snippet = f["content"][:max_chars]
        if len(f["content"]) > max_chars:
            snippet += "\n... (truncated)"
        parts.append(f"### {f['path']}\n```\n{snippet}\n```")
    return "\n\n".join(parts)


# ── Agent 1: Difficulty Assessor ──────────────────────────────────────────────

_DIFFICULTY_SYSTEM = """You are a senior software engineer assessing codebase difficulty.
Return ONLY valid JSON (no markdown fences, no extra text) with exactly these keys:
{
  "level": "Beginner" | "Intermediate" | "Advanced",
  "reason": "<1-2 sentence explanation>",
  "primary_language": "<language name>",
  "frameworks": ["<framework1>", ...]
}

Criteria:
- Beginner: single language, simple scripts, no design patterns, few files
- Intermediate: multiple modules, some patterns (MVC, REST), moderate complexity
- Advanced: distributed systems, complex patterns, multiple languages, security layers"""


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

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())


# ── Agent 2: Explainer ────────────────────────────────────────────────────────

_EXPLAINER_SYSTEM = """You are a patient, knowledgeable coding mentor.
Explain codebases in plain language, adapting your style to the difficulty level:
- Beginner: simple analogies, avoid jargon, explain what each file does
- Intermediate: architecture patterns, data flow, module responsibilities
- Advanced: design decisions, tradeoffs, scalability, non-obvious patterns

Structure your response as markdown with clear headings."""


def explain_codebase(ingestion_result: dict, difficulty: dict) -> str:
    file_snippets = _format_files(ingestion_result["files"], _MAX_EXPLAINER_FILES, _MAX_FILE_CHARS)

    user_msg = f"""Difficulty: {difficulty["level"]} — {difficulty["reason"]}
Language: {difficulty["primary_language"]}
Frameworks: {", ".join(difficulty.get("frameworks", [])) or "none detected"}

File tree:
{ingestion_result["file_tree"]}

Key file snippets:
{file_snippets}

Write a plain-language explanation of this codebase for a {difficulty["level"]} level developer."""

    return _chat(_EXPLAINER_SYSTEM, user_msg)


# ── Agent 3: Planner ──────────────────────────────────────────────────────────

_PLANNER_SYSTEM = """You are a pragmatic software architect.
Given a codebase explanation, produce a realistic phased development plan.
Structure: Phase 0 (MVP) → Phase 1 (core features) → Phase 2 (scale/security/polish).
Each phase must include: Goals, Key tasks, Security considerations.
Format as clean markdown."""


def generate_plan(ingestion_result: dict, explanation: str) -> str:
    user_msg = f"""Codebase explanation:
{explanation}

File tree:
{ingestion_result["file_tree"]}

Generate a phased implementation/improvement plan with security considerations per phase."""

    return _chat(_PLANNER_SYSTEM, user_msg)


# ── Agent 4: Diagram ──────────────────────────────────────────────────────────

_DIAGRAM_SYSTEM = """You are a software architect. Given a file tree, output a Mermaid diagram
showing the main modules and how they relate. Use 'graph TD' syntax only.
Keep it simple — max 12 nodes. Output ONLY the raw Mermaid code, no fences, no explanation."""


def generate_diagram(ingestion_result: dict) -> str:
    user_msg = f"""File tree:
{ingestion_result["file_tree"]}

Generate a Mermaid graph TD diagram showing the main modules and their relationships."""

    raw = _chat(_DIAGRAM_SYSTEM, user_msg, temperature=0.1)
    # Strip fences if present
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            if part.startswith("mermaid"):
                raw = part[7:].strip()
                break
            elif part.strip().startswith("graph"):
                raw = part.strip()
                break
    return raw.strip()


# ── Agent 5: Security Auditor ─────────────────────────────────────────────────

_SECURITY_SYSTEM = """You are a security engineer reviewing source code for vulnerabilities.
Scan for these specific issues and return ONLY valid JSON (no fences, no extra text):
{
  "summary": "<1-2 sentence overall security posture>",
  "risk_level": "Low" | "Medium" | "High" | "Critical",
  "findings": [
    {
      "severity": "low" | "medium" | "high" | "critical",
      "category": "secret" | "injection" | "exposed_env" | "weak_auth" | "other",
      "file": "<path>",
      "issue": "<what's wrong>",
      "fix": "<how to fix it>"
    }
  ]
}

Look for: hardcoded API keys/passwords/tokens, SQL injection (string concat in queries),
exposed environment variables in client code, weak password rules, missing auth checks,
unsafe deserialisation, command injection. Be concrete — quote the file path.
If nothing concerning is found, return an empty findings array and risk_level "Low"."""


def audit_security(ingestion_result: dict) -> dict:
    files = _format_files(ingestion_result["files"], _MAX_EXPLAINER_FILES, _MAX_FILE_CHARS)
    user_msg = f"""File tree:
{ingestion_result["file_tree"]}

Code to audit:
{files}"""

    raw = _chat(_SECURITY_SYSTEM, user_msg, temperature=0.1)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return {"summary": "Security audit parse failed", "risk_level": "Low", "findings": []}


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_pipeline(ingestion_result: dict) -> dict:
    """Run all five agents in sequence."""
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
