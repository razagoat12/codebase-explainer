"""
Three-agent Gemini pipeline:
  1. Difficulty Assessor  → returns structured JSON
  2. Explainer            → returns plain-language markdown explanation
  3. Planner              → returns phased plan markdown
"""
import json

import google.generativeai as genai

from app.config import settings

genai.configure(api_key=settings.gemini_api_key)

MODEL = "gemini-2.0-flash"
_GENERATION_CONFIG = genai.types.GenerationConfig(temperature=0.3, max_output_tokens=8192)


def _model() -> genai.GenerativeModel:
    return genai.GenerativeModel(MODEL, generation_config=_GENERATION_CONFIG)


def _format_files(files: list[dict]) -> str:
    parts = []
    for f in files:
        parts.append(f"### {f['path']}\n```\n{f['content']}\n```")
    return "\n\n".join(parts)


# ── Agent 1: Difficulty Assessor ──────────────────────────────────────────────

_DIFFICULTY_PROMPT = """You are a senior software engineer assessing a codebase.
Analyse the file tree, language stats, and file contents below.
Return ONLY valid JSON (no markdown fences) with exactly these keys:
{{
  "level": "Beginner" | "Intermediate" | "Advanced",
  "reason": "<1-2 sentence explanation>",
  "primary_language": "<language name>",
  "frameworks": ["<framework1>", ...]
}}

Criteria:
- Beginner: single language, simple scripts, no design patterns, few files
- Intermediate: multiple files/modules, some patterns (MVC, REST), moderate complexity
- Advanced: distributed systems, complex patterns, multiple languages, security layers

File tree:
{file_tree}

Language stats:
{lang_stats}

File contents (sample):
{file_contents}
"""


def assess_difficulty(ingestion_result: dict) -> dict:
    file_tree = ingestion_result["file_tree"]
    stats = ingestion_result["stats"]
    lang_stats = json.dumps(stats["language_counts"], indent=2)

    # Send only first 20 files to keep prompt size manageable
    sample_files = ingestion_result["files"][:20]
    file_contents = _format_files(sample_files)

    prompt = _DIFFICULTY_PROMPT.format(
        file_tree=file_tree, lang_stats=lang_stats, file_contents=file_contents
    )

    response = _model().generate_content(prompt)
    raw = response.text.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw)


# ── Agent 2: Explainer ────────────────────────────────────────────────────────

_EXPLAINER_SYSTEM = """You are a patient, knowledgeable coding mentor.
Explain codebases in plain language, adapting your style to the difficulty level:
- Beginner: use simple analogies, avoid jargon, explain what each file does step-by-step
- Intermediate: describe architecture patterns, data flow, and module responsibilities
- Advanced: focus on design decisions, tradeoffs, scalability, and non-obvious patterns

Always structure your response as markdown with clear headings."""

_EXPLAINER_PROMPT = """Difficulty level: {level} ({reason})
Primary language: {primary_language}
Frameworks detected: {frameworks}

File tree:
{file_tree}

File contents:
{file_contents}

Write a thorough plain-language explanation of this codebase for someone at the {level} level."""


def explain_codebase(ingestion_result: dict, difficulty: dict) -> str:
    file_tree = ingestion_result["file_tree"]
    file_contents = _format_files(ingestion_result["files"])

    prompt = _EXPLAINER_PROMPT.format(
        level=difficulty["level"],
        reason=difficulty["reason"],
        primary_language=difficulty["primary_language"],
        frameworks=", ".join(difficulty.get("frameworks", [])) or "none detected",
        file_tree=file_tree,
        file_contents=file_contents,
    )

    model = genai.GenerativeModel(
        MODEL,
        system_instruction=_EXPLAINER_SYSTEM,
        generation_config=_GENERATION_CONFIG,
    )
    response = model.generate_content(prompt)
    return response.text.strip()


# ── Agent 3: Planner ──────────────────────────────────────────────────────────

_PLANNER_SYSTEM = """You are a pragmatic software architect.
Given a codebase explanation and structure, produce a realistic phased development plan.
Focus on: MVP → Phase 1 → Phase 2. Each phase must include:
- Goals (what will work when this phase is done)
- Key tasks (concrete, actionable)
- Security considerations for this phase
Format everything as clean markdown."""

_PLANNER_PROMPT = """Codebase explanation:
{explanation}

File tree:
{file_tree}

Generate a phased implementation/improvement plan for this codebase.
Phase 0 should be the true MVP (minimal viable), Phase 1 adds core features,
Phase 2 adds scale/security/polish. Include security considerations per phase."""


def generate_plan(ingestion_result: dict, explanation: str) -> str:
    prompt = _PLANNER_PROMPT.format(
        explanation=explanation, file_tree=ingestion_result["file_tree"]
    )

    model = genai.GenerativeModel(
        MODEL,
        system_instruction=_PLANNER_SYSTEM,
        generation_config=_GENERATION_CONFIG,
    )
    response = model.generate_content(prompt)
    return response.text.strip()


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_pipeline(ingestion_result: dict) -> dict:
    """Run all three agents in sequence. Returns {difficulty, explanation, plan}."""
    difficulty = assess_difficulty(ingestion_result)
    explanation = explain_codebase(ingestion_result, difficulty)
    plan = generate_plan(ingestion_result, explanation)
    return {"difficulty": difficulty, "explanation": explanation, "plan": plan}
