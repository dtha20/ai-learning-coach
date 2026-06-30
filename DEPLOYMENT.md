# DEPLOYMENT.md — Production Deployment Guide

This guide covers running AI Learning Coach as a persistent service on
Ubuntu 24.04 LTS, plus Docker, backups, and troubleshooting.

---

## Option A: systemd service (recommended)

Create the unit file:

```bash
sudo nano /etc/systemd/system/ai-learning-coach.service
```

```ini
[Unit]
Description=AI Learning Coach - daily lesson scheduler
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=aicoach
Group=aicoach
WorkingDirectory=/home/aicoach/ai-learning-coach
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/aicoach/ai-learning-coach/.venv/bin/python -m ai_learning_coach.main schedule
Restart=on-failure
RestartSec=10
StandardOutput=append:/home/aicoach/ai-learning-coach/logs/systemd.log
StandardError=append:/home/aicoach/ai-learning-coach/logs/systemd.log

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-learning-coach
sudo systemctl start ai-learning-coach
sudo systemctl status ai-learning-coach
```

View logs:

```bash
journalctl -u ai-learning-coach -f
# or
tail -f /home/aicoach/ai-learning-coach/logs/ai_learning_coach.log
```

Restart after a config or code change:

```bash
sudo systemctl restart ai-learning-coach
```

---

## Option B: cron (alternative to APScheduler daemon)

If you'd rather not run a long-lived process, use the `run` CLI command
(single-shot) and let cron handle scheduling instead of APScheduler:

```bash
crontab -e -u aicoach
```

Add (example: run daily at 08:00 server time):

```cron
0 8 * * * cd /home/aicoach/ai-learning-coach && /home/aicoach/ai-learning-coach/.venv/bin/python -m ai_learning_coach.main run >> logs/cron.log 2>&1
```

Note: with cron, `LESSON_TIME` in `.env` is only used by the `schedule`
command — when using cron, the cron expression itself controls timing, so
keep the two in sync if you reference `LESSON_TIME` elsewhere.

---

## Option C: Docker / docker-compose

```bash
cp .env.example .env   # fill in secrets
docker compose up -d --build
docker compose logs -f
```

To run a one-off immediate lesson (for testing) inside the container:

```bash
docker compose run --rm ai-learning-coach run --debug
```

Data and logs persist on the host via the `./data` and `./logs` bind mounts
defined in `docker-compose.yml`.

Update and redeploy:

```bash
git pull
docker compose up -d --build
```

---

## Backup and Restore

### What to back up

- `data/learning_coach.db` — SQLite database (completion state + history).
- `.env` — your secrets (back up securely, not in plain git).
- `ai_learning_coach/curriculum/data/*.json` — if you've customized the
  curriculum.

### Backup

```bash
mkdir -p backups
cp data/learning_coach.db backups/learning_coach_$(date +%Y%m%d_%H%M%S).db
tar -czf backups/curriculum_$(date +%Y%m%d).tar.gz ai_learning_coach/curriculum/data
```

Automate with a daily cron entry:

```cron
30 2 * * * cp /home/aicoach/ai-learning-coach/data/learning_coach.db /home/aicoach/ai-learning-coach/backups/learning_coach_$(date +\%Y\%m\%d).db
```

### Restore

```bash
sudo systemctl stop ai-learning-coach
cp backups/learning_coach_20260101_020000.db data/learning_coach.db
sudo systemctl start ai-learning-coach
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Service won't start | Wrong path in `ExecStart`, or venv missing | Verify `.venv/bin/python` exists and paths match your install dir |
| `Configuration error: Missing required environment variable` | `.env` not found by systemd's `WorkingDirectory` | Ensure `.env` is in the same directory as `WorkingDirectory` |
| Lesson never arrives in Telegram | Bot not in group / wrong chat ID | Re-verify `TELEGRAM_CHAT_ID` per CONFIG.md, ensure bot is a group member with send permission |
| `GeminiError: ... after 3 attempts` | Invalid API key, quota exceeded, or network/firewall issue | Check `GEMINI_API_KEY`, check outbound HTTPS access to `generativelanguage.googleapis.com` |
| `TelegramError: ... after 3 attempts` | Invalid bot token, or outbound HTTPS blocked | Check `TELEGRAM_BOT_TOKEN`, test with `curl https://api.telegram.org/bot<token>/getMe` |
| Same lesson posted twice | Manual `run` invoked alongside the scheduler, or system clock skew | Use `history` command to check for duplicate publish dates; rely on one runner (cron OR scheduler, not both) |
| Curriculum "runs dry" | Should never happen — modules auto-cycle | If it does, check `CurriculumError` in logs; verify JSON files are valid |
| Logs growing too large | Rotation misconfigured | Rotation is automatic (5MB x 5 backups); check `ai_learning_coach/logger.py` if you've modified it |

### Health check command

```bash
python -m ai_learning_coach.main history --limit 5
```

Shows the last 5 publish attempts with status, timing, and any error
message — the fastest way to confirm the system is healthy.

### Firewall / outbound access

The service needs outbound HTTPS (443) access to:

- `generativelanguage.googleapis.com` (Gemini API)
- `api.telegram.org` (Telegram Bot API)

If running behind a restrictive egress firewall, allowlist both hosts.
