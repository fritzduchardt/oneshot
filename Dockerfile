FROM python:3.14.3-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PORT=8080

WORKDIR /app

COPY ./pyproject.toml /app/pyproject.toml
COPY ./src /app/src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e . \
    && adduser --disabled-password --gecos "" --home /app --no-create-home oneshot \
    && chown -R oneshot:oneshot /app

USER oneshot

EXPOSE 8080

ENTRYPOINT ["python", "-m", "oneshot.server"]
