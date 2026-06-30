"""Unit tests for ai_learning_coach.lesson.engine."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ai_learning_coach.curriculum.engine import CurriculumTopic
from ai_learning_coach.lesson.engine import LessonEngine, LessonGenerationError

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "ai_learning_coach" / "lesson" / "templates"

LESSON_JSON = {
    "title": "What is Prompt Engineering?",
    "objectives": ["Understand prompts", "Write better prompts"],
    "why_it_matters": "Because prompts drive LLM output quality.",
    "concept_explanation": "Prompt engineering is the practice of designing inputs.",
    "real_world_example": "Writing a support-ticket triage prompt.",
    "copy_ready_prompt": "Classify this ticket: {ticket}",
    "common_mistakes": ["Being vague"],
    "best_practices": ["Be specific"],
    "recommended_tools": ["Gemini", "Claude"],
    "five_minute_exercise": "Write 3 prompts for the same task.",
    "advanced_challenge": "Build a prompt template library.",
    "summary": "Good prompts are specific and structured.",
}


def _topic(lesson_type: str = "lesson") -> CurriculumTopic:
    return CurriculumTopic(
        lesson_id="mon-01",
        module="prompt_engineering",
        title="What is Prompt Engineering?",
        weekday="monday",
        lesson_type=lesson_type,
    )


def test_generate_lesson_renders_markdown() -> None:
    fake_gemini = MagicMock()
    fake_gemini.generate.return_value = json.dumps(LESSON_JSON)
    engine = LessonEngine(fake_gemini, TEMPLATES_DIR)

    result = engine.generate(_topic("lesson"))

    assert "What is Prompt Engineering?" in result.markdown
    assert "Learning Objectives" in result.markdown
    assert result.lesson_type == "lesson"


def test_generate_lesson_strips_code_fences() -> None:
    fake_gemini = MagicMock()
    fake_gemini.generate.return_value = f"```json\n{json.dumps(LESSON_JSON)}\n```"
    engine = LessonEngine(fake_gemini, TEMPLATES_DIR)

    result = engine.generate(_topic("lesson"))

    assert "Concept Explanation" in result.markdown


def test_generate_lesson_invalid_json_raises() -> None:
    fake_gemini = MagicMock()
    fake_gemini.generate.return_value = "not valid json {{{"
    engine = LessonEngine(fake_gemini, TEMPLATES_DIR)

    with pytest.raises(LessonGenerationError):
        engine.generate(_topic("lesson"))


def test_generate_quiz_requires_exactly_five_questions() -> None:
    fake_gemini = MagicMock()
    quiz_data = {
        "title": "Weekly Review",
        "summary": "Recap",
        "questions": [
            {
                "question": "Q1?",
                "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
                "correct_answer": "A",
                "explanation": "Because.",
            }
        ],
    }
    fake_gemini.generate.return_value = json.dumps(quiz_data)
    engine = LessonEngine(fake_gemini, TEMPLATES_DIR)

    with pytest.raises(LessonGenerationError):
        engine.generate(_topic("quiz"))
