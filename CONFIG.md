# CONFIG.md — Configuration Reference

All configuration is read from environment variables, typically supplied via
a `.env` file in the project root (loaded automatically by
`ai_learning_coach.config`). Copy `.env.example` to `.env` and edit it.

## Required Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | API key for Google Gemini. Get one at https://aistudio.google.com/app/apikey |
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) on Telegram. |
| `TELEGRAM_CHAT_ID` | Numeric ID of the target group/channel (negative for groups, e.g. `-1001234567890`). Add your bot to the group as an admin first. |

## Scheduling Variables

| Variable | Default | Description |
|---|---|---|
| `TIMEZONE` | `UTC` | IANA timezone name, e.g. `Europe/Rome`, `America/New_York`. |
| `LESSON_TIME` | `08:00` | 24-hour `HH:MM` local time when the daily lesson is published. |

## Optional / Advanced Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model identifier. |
| `GEMINI_TIMEOUT` | `60` | HTTP timeout (seconds) per Gemini request. |
| `GEMINI_MAX_RETRIES` | `3` | Retry attempts on Gemini failures (with exponential backoff). |
| `TELEGRAM_MAX_RETRIES` | `3` | Retry attempts on Telegram send failures. |
| `LOG_LEVEL` | `INFO` | `INFO` or `DEBUG`. Use `--debug` CLI flag to force DEBUG for one run. |
| `LOG_DIR` | `./logs` | Directory for rotating log files. |
| `DB_PATH` | `./data/learning_coach.db` | SQLite database file path. |
| `CURRICULUM_DIR` | `./ai_learning_coach/curriculum/data` | Directory containing the 7 weekday JSON curriculum files. |
| `TEMPLATES_DIR` | `./ai_learning_coach/lesson/templates` | Directory containing the 3 Jinja2 `.md.j2` templates. |

## How to find your Telegram Chat ID

1. Add your bot to the target group.
2. Send any message in the group.
3. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in a
   browser.
4. Look for `"chat":{"id": -100XXXXXXXXXX, ...}` in the JSON response — that
   number (including the minus sign) is your `TELEGRAM_CHAT_ID`.

## Customizing the curriculum

Each weekday has its own JSON file under
`ai_learning_coach/curriculum/data/<weekday>.json`:

```json
{
  "weekday": "monday",
  "module": "prompt_engineering",
  "lessons": [
    {"id": "mon-01", "title": "What is Prompt Engineering?", "sequence": 1},
    {"id": "mon-02", "title": "Zero-shot vs Few-shot Prompting", "sequence": 2}
  ]
}
```

- `id` must be unique across the whole curriculum.
- `sequence` controls publish order within that weekday.
- Saturday/Sunday files additionally set `"lesson_type": "mini_project"` and
  `"lesson_type": "quiz"` respectively.
- You can freely add, remove, or reorder lessons. New `id`s are picked up
  automatically on the next run (the engine seeds new lessons into the
  database without touching existing completion state).
- Once every lesson in a module is completed, the module automatically
  resets and cycles again — the curriculum never "runs dry".

## Customizing lesson templates

Templates live in `ai_learning_coach/lesson/templates/*.md.j2` and use
standard Jinja2 syntax with Telegram Markdown formatting (`*bold*`,
`_italic_`, `` ```code``` ``). Edit them to change tone, emoji, or layout —
no Python changes required.
