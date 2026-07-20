FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
RUN useradd --create-home aps \
    && mkdir -p /app/data \
    && chown -R aps:aps /app

USER aps

CMD ["python", "-m", "aps_bot"]
