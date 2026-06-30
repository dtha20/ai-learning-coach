FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ai_learning_coach ./ai_learning_coach
COPY .env.example ./.env.example

RUN mkdir -p /app/data /app/logs

VOLUME ["/app/data", "/app/logs"]

ENTRYPOINT ["python", "-m", "ai_learning_coach.main"]
CMD ["schedule"]
