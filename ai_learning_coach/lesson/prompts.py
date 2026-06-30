"""Prompt builders for AI Learning Coach.

These functions build the exact instructions sent to Gemini. The *topic*
(title/module) is always fixed by the curriculum engine beforehand — these
prompts explicitly forbid Gemini from inventing or changing the topic, and
require strict JSON output so it can be reliably rendered via Jinja2.
"""

from __future__ import annotations

LESSON_JSON_SCHEMA_HINT = """
Respond with ONLY a single valid JSON object (no markdown fences, no commentary)
with exactly these string/array fields:
{
  "title": "string - must match the given lesson title exactly",
  "objectives": ["string", "string", "..."],
  "why_it_matters": "string (2-4 sentences)",
  "concept_explanation": "string (clear, technical, several paragraphs, use \\n for line breaks)",
  "real_world_example": "string",
  "copy_ready_prompt": "string - a ready-to-use AI prompt the reader can copy/paste",
  "common_mistakes": ["string", "string", "..."],
  "best_practices": ["string", "string", "..."],
  "recommended_tools": ["string", "string", "..."],
  "five_minute_exercise": "string",
  "advanced_challenge": "string",
  "summary": "string (2-3 sentences)"
}
"""


def build_lesson_prompt(title: str, module: str, weekday: str) -> str:
    """Build the Gemini prompt for a standard daily lesson.

    Args:
        title: Fixed lesson title selected by the curriculum engine.
        module: Curriculum module name (e.g. "prompt_engineering").
        weekday: Weekday name (e.g. "monday").

    Returns:
        The full prompt string to send to Gemini.
    """
    return f"""You are an expert technical instructor creating a daily micro-lesson
for IT engineers (network engineers, Python developers, DevOps engineers, and
AI practitioners) studying as part of a structured curriculum.

The lesson topic is FIXED and must NOT be changed, renamed, or reinterpreted:
- Module: {module}
- Weekday: {weekday}
- Lesson title: "{title}"

Do not invent a different topic. Generate ONLY the educational content for
this exact topic, written for an audience that already knows general IT
concepts but may be new to this specific subject. Be precise, practical,
and avoid filler.
{LESSON_JSON_SCHEMA_HINT}
"""


def build_mini_project_prompt(title: str, module: str) -> str:
    """Build the Gemini prompt for a Saturday mini-project.

    Args:
        title: Fixed mini-project title selected by the curriculum engine.
        module: Curriculum module name (always "mini_project" on Saturdays).

    Returns:
        The full prompt string to send to Gemini.
    """
    return f"""You are an expert technical instructor designing a hands-on mini-project
for IT engineers, completable in 30 to 60 minutes.

The project topic is FIXED and must NOT be changed or reinterpreted:
- Title: "{title}"
- Category: {module}

Respond with ONLY a single valid JSON object (no markdown fences, no commentary)
with exactly these fields:
{{
  "title": "string - must match the given title exactly",
  "estimated_time": "string, e.g. '45 minutes'",
  "objectives": ["string", "string", "..."],
  "requirements": ["string", "string", "..."],
  "steps": ["string", "string", "..."],
  "deliverables": ["string", "string", "..."],
  "hints": ["string", "string", "..."],
  "extension_ideas": ["string", "string", "..."]
}}
"""


def build_quiz_prompt(title: str, weekday_topics: list[str]) -> str:
    """Build the Gemini prompt for the Sunday review quiz.

    Args:
        title: Fixed quiz/review title selected by the curriculum engine.
        weekday_topics: List of module names covered during the week, used
            to give Gemini context for relevant review questions.

    Returns:
        The full prompt string to send to Gemini.
    """
    topics_str = ", ".join(weekday_topics) if weekday_topics else "general IT and AI topics"
    return f"""You are an expert technical instructor creating a weekly review quiz
for IT engineers studying: {topics_str}.

The quiz title is FIXED and must NOT be changed:
- Title: "{title}"

Create EXACTLY 5 multiple-choice questions covering this week's themes.

Respond with ONLY a single valid JSON object (no markdown fences, no commentary):
{{
  "title": "string - must match the given title exactly",
  "summary": "string - 2-3 sentence recap of the week's themes",
  "questions": [
    {{
      "question": "string",
      "options": {{"A": "string", "B": "string", "C": "string", "D": "string"}},
      "correct_answer": "A|B|C|D",
      "explanation": "string"
    }}
  ]
}}
The "questions" array MUST contain exactly 5 items.
"""
