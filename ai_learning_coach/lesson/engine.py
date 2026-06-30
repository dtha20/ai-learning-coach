"""Lesson engine for AI Learning Coach.

Orchestrates the full content-generation pipeline for a single topic chosen
by the curriculum engine:

1. Build the appropriate Gemini prompt (lesson / mini_project / quiz).
2. Call Gemini and parse its strict-JSON response.
3. Render the parsed content into Telegram-ready Markdown via Jinja2.

Gemini is sandboxed to *content only* — the topic/title is always injected
by the caller and the rendered template always re-displays the curriculum's
title, so Gemini cannot silently swap topics.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ai_learning_coach.curriculum.engine import CurriculumTopic
from ai_learning_coach.database.models import today_iso
from ai_learning_coach.gemini.client import GeminiClient
from ai_learning_coach.lesson.prompts import (
    build_lesson_prompt,
    build_mini_project_prompt,
    build_quiz_prompt,
)

logger = logging.getLogger(__name__)

WEEKLY_MODULE_NAMES = {
    "monday": "Prompt Engineering",
    "tuesday": "OpenClaw & AI Agents",
    "wednesday": "Cisco/F5 Automation",
    "thursday": "Python & Programming",
    "friday": "Advanced Prompting & AI Trends",
}


class LessonGenerationError(RuntimeError):
    """Raised when content generation or rendering fails."""


@dataclass(frozen=True)
class GeneratedLesson:
    """Final rendered output ready to publish.

    Attributes:
        markdown: Telegram-ready Markdown text.
        title: The lesson/quiz/project title actually used.
        lesson_type: One of "lesson", "mini_project", "quiz".
    """

    markdown: str
    title: str
    lesson_type: str


class LessonEngine:
    """Generates and renders a single day's lesson content."""

    def __init__(self, gemini_client: GeminiClient, templates_dir: Path) -> None:
        """Initialize the lesson engine.

        Args:
            gemini_client: Configured `GeminiClient` instance.
            templates_dir: Directory containing the Jinja2 `.md.j2` templates.
        """
        self.gemini = gemini_client
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(disabled_extensions=("j2",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, topic: CurriculumTopic) -> GeneratedLesson:
        """Generate and render content for the given curriculum topic.

        Args:
            topic: The fixed topic selected by the curriculum engine.

        Returns:
            A `GeneratedLesson` with final Markdown ready for Telegram.

        Raises:
            LessonGenerationError: If Gemini output cannot be parsed/rendered.
        """
        if topic.lesson_type == "mini_project":
            return self._generate_mini_project(topic)
        if topic.lesson_type == "quiz":
            return self._generate_quiz(topic)
        return self._generate_lesson(topic)

    # ------------------------------------------------------------------ #
    # Generation per lesson type
    # ------------------------------------------------------------------ #

    def _generate_lesson(self, topic: CurriculumTopic) -> GeneratedLesson:
        prompt = build_lesson_prompt(topic.title, topic.module, topic.weekday)
        data = self._call_and_parse(prompt)
        data["title"] = topic.title  # enforce curriculum title, ignore any drift
        data["weekday"] = topic.weekday
        data["module"] = topic.module
        data["publish_date"] = today_iso()
        markdown = self._render("lesson.md.j2", data)
        return GeneratedLesson(markdown=markdown, title=topic.title, lesson_type="lesson")

    def _generate_mini_project(self, topic: CurriculumTopic) -> GeneratedLesson:
        prompt = build_mini_project_prompt(topic.title, topic.module)
        data = self._call_and_parse(prompt)
        data["title"] = topic.title
        data["publish_date"] = today_iso()
        markdown = self._render("mini_project.md.j2", data)
        return GeneratedLesson(markdown=markdown, title=topic.title, lesson_type="mini_project")

    def _generate_quiz(self, topic: CurriculumTopic) -> GeneratedLesson:
        weekday_topics = list(WEEKLY_MODULE_NAMES.values())
        prompt = build_quiz_prompt(topic.title, weekday_topics)
        data = self._call_and_parse(prompt)
        data["title"] = topic.title
        data["publish_date"] = today_iso()

        questions = data.get("questions", [])
        if len(questions) != 5:
            raise LessonGenerationError(
                f"Expected exactly 5 quiz questions, got {len(questions)}"
            )
        markdown = self._render("quiz.md.j2", data)
        return GeneratedLesson(markdown=markdown, title=topic.title, lesson_type="quiz")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _call_and_parse(self, prompt: str) -> dict[str, Any]:
        """Call Gemini and parse its response as JSON, tolerating minor noise.

        Args:
            prompt: The fully-built prompt to send.

        Returns:
            Parsed JSON content as a dict.

        Raises:
            LessonGenerationError: If the response cannot be parsed as JSON.
        """
        raw = self.gemini.generate(prompt)
        cleaned = self._strip_code_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Gemini JSON. Raw output: %s", raw[:2000])
            raise LessonGenerationError(f"Could not parse Gemini response as JSON: {exc}") from exc

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove ```json ... ``` or ``` ... ``` fences if Gemini added them."""
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        return match.group(1) if match else text

    def _render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a Jinja2 template with the given context.

        Args:
            template_name: File name of the template within `templates_dir`.
            context: Variables to pass into the template.

        Returns:
            Rendered Markdown string.

        Raises:
            LessonGenerationError: If rendering fails (e.g. missing key).
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context).strip()
        except Exception as exc:  # noqa: BLE001 - surfaced as a domain error
            raise LessonGenerationError(f"Failed to render {template_name}: {exc}") from exc
