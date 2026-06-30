# INSTALL.md — Ubuntu Server Installation Guide

Tested on **Ubuntu 24.04 LTS** with **Python 3.12+**.

## 1. Update the system

```bash
sudo apt update && sudo apt upgrade -y
```

## 2. Install Python 3.12 and prerequisites

Ubuntu 24.04 ships with Python 3.12 by default. Verify:

```bash
python3 --version    # should report Python 3.12.x
```

If it's missing, install it:

```bash
sudo apt install -y python3 python3-venv python3-pip git
```

## 3. Create a dedicated system user (recommended)

Running as a non-root service user is good practice:

```bash
sudo useradd -m -s /bin/bash aicoach
sudo su - aicoach
```

## 4. Clone the project

```bash
git clone <your-repo-url> ai-learning-coach
cd ai-learning-coach
```

## 5. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 6. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 7. Configure environment variables

```bash
cp .env.example .env
nano .env
```

Fill in at minimum:

```
GEMINI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TIMEZONE=Europe/Rome
LESSON_TIME=08:00
```

See **[CONFIG.md](CONFIG.md)** for the full list of options.

## 8. Verify the installation

Run the pipeline once, immediately, to confirm everything works end-to-end:

```bash
python -m ai_learning_coach.main run --debug
```

You should see log lines for: curriculum loaded → topic selected → Gemini
content generated → Telegram message sent → history recorded. Check your
Telegram group for the message.

## 9. Run the test suite (optional but recommended)

```bash
pip install pytest pytest-mock
pytest -v
```

## 10. Set up as a persistent service

Continue to **[DEPLOYMENT.md](DEPLOYMENT.md)** to configure systemd (or
cron) so the scheduler survives reboots and runs continuously.

## Troubleshooting installation

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | venv not activated, or deps not installed | `source .venv/bin/activate && pip install -r requirements.txt` |
| `Configuration error: Missing required environment variable` | `.env` not filled in or not in project root | Confirm `.env` exists next to `requirements.txt` |
| `pip install` fails for cryptography-related deps | Missing build tools | `sudo apt install -y build-essential python3-dev` |
| Permission denied writing to `data/` or `logs/` | Wrong file ownership | `sudo chown -R aicoach:aicoach /home/aicoach/ai-learning-coach` |
