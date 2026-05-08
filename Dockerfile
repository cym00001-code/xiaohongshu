FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN python -m pip install --upgrade pip

COPY pyproject.toml README.md ./
COPY src ./src
COPY settings.yaml tags.yaml ./

RUN python -m pip install .

CMD ["daily-digest", "schedule"]
