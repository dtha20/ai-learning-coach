# AI Learning Coach

A production-ready Python application that automatically generates one AI/IT
lesson every day using the **Gemini API** and posts it to a **Telegram
group**. Built for IT engineers studying Prompt Engineering, AI Agents,
Cisco/F5 Automation, Python, DevOps, and AI Trends.

## Why this project exists

Most "learn AI" content is either too shallow or too scattered. AI Learning
Coach delivers one focused, well-structured lesson per day, every day,
forever — following a fixed weekly curriculum so you always know what's
coming and never run out of material.

## Weekly Curriculum

| Day       | Module                              |
|-----------|--------------------------------------|
| Monday    | Prompt Engineering                  |
| Tuesday   | OpenClaw & AI Agents                |
| Wednesday | Cisco/F5 Network Automation         |
| Thursday  | Python & Programming                |
| Friday    | Advanced Prompting + AI Trends      |
| Saturday  | Mini Project (30–60 minutes)        |
| Sunday    | Review + 5-Question Quiz            |

## How it works

1. **Curriculum Engine** picks the next *unfinished* topic for today's
   weekday from a JSON file (`ai_learning_coach/curriculum/data/*.json`).
   Gemini never invents topics — it only writes the content for the topic
   it's told to write about.
2. **Lesson Engine** builds a strict prompt, calls **Gemini 2.5 Flash** for
   structured JSON content, and renders it into Telegram-ready Markdown via
   **Jinja2** templates.
3. **Telegram Client** posts the Markdown to your group, splitting long
   messages and handling rate limits automatically.
4. **Database (SQLite)** tracks which lessons are completed and logs every
   publish attempt (success/failure, timing) to `history`.
5. **Scheduler (APScheduler)** runs this pipeline once a day at your
   configured local time — or you can trigger it instantly via the CLI.

## Project Structure

```
ai-learning-coach/
├── ai_learning_coach/
│   ├── config.py              # .env-based settings loader
│   ├── logger.py               # rotating log setup
│   ├── coach.py                 # top-level orchestrator
│   ├── main.py                  # CLI entrypoint
│   ├── database/                # SQLite models + access layer
│   ├── curriculum/               # JSON curriculum + selection engine
│   │   └── data/*.json
│   ├── gemini/                   # Gemini REST client
│   ├── telegram/                 # Telegram Bot API client
│   ├── lesson/                   # prompt builders + Jinja2 rendering
│   │   └── templates/*.md.j2
│   ├── scheduler/                 # APScheduler wrapper
│   └── utils/                     # generic helpers
├── tests/                          # pytest unit tests
├── docs/                           # additional documentation
├── Dockerfile / docker-compose.yml
├── requirements.txt / pyproject.toml
├── .env.example
└── README.md (this file)
```

## Quick Start

```bash
git clone <this-repo> ai-learning-coach
cd ai-learning-coach
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your secrets
python -m ai_learning_coach.main run            # run once, immediately
python -m ai_learning_coach.main schedule       # run forever, daily at LESSON_TIME
```

See **[INSTALL.md](INSTALL.md)** for full Ubuntu setup,
**[CONFIG.md](CONFIG.md)** for all configuration options, and
**[DEPLOYMENT.md](DEPLOYMENT.md)** for systemd/cron/Docker deployment,
backup, and troubleshooting.

## CLI Reference

```bash
python -m ai_learning_coach.main run [--weekday monday] [--debug]
python -m ai_learning_coach.main schedule [--debug]
python -m ai_learning_coach.main history [--limit 10]
```

## Lesson Format

Every standard lesson includes: Title, Learning Objectives, Why This
Matters, Concept Explanation, Real-World Example, a Copy-Ready Prompt,
Common Mistakes, Best Practices, Recommended Tools, a 5-Minute Exercise, an
Advanced Challenge, and a Summary — rendered as Telegram Markdown.

Saturdays generate a 30–60 minute **Mini Project** (objectives,
requirements, steps, deliverables, hints, extension ideas). Sundays generate
a **Review + 5-question multiple-choice Quiz** with explanations.

## Testing

```bash
pytest -v
```

Unit tests cover the curriculum engine, database layer, Gemini client,
Telegram client, lesson engine, and scheduler — all using mocks, so no real
API keys or network access are required to run the test suite.

## Design Principles

- **Clean Architecture**: each concern (config, db, curriculum, AI, messaging,
  rendering, scheduling) lives in its own module with a narrow interface.
- **SOLID**: e.g. `LessonEngine` depends on an abstract-enough `GeminiClient`
  interface; `CurriculumEngine` never depends on Gemini or Telegram at all.
- **Gemini is content-only**: topic selection is 100% deterministic and
  database-tracked; Gemini cannot change what topic is taught.
- **Fail-safe**: every publish attempt — success or failure — is recorded in
  `history` with timing and error details for observability.

## License

Use, modify, and deploy freely for personal or organizational learning
programs.
