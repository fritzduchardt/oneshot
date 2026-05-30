FROM python:3.14.3-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PORT=8000

WORKDIR /app

COPY ./pyproject.toml /app/pyproject.toml
COPY ./src /app/src

# Install gevent for async worker support required by SSE endpoints
# Install gevent-websocket for WebSocket/streaming protocol support used by MCP servers
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e . gevent gevent-websocket \
    && adduser --disabled-password --gecos "" --home /app --no-create-home oneshot \
    && chown -R oneshot:oneshot /app

USER oneshot

EXPOSE 8000

# Use gevent worker class to prevent SSE connections from blocking other requests
# gevent provides cooperative multitasking so long-lived SSE connections don't starve the worker
# workers=1 with gevent handles many concurrent connections via greenlets
# --timeout 0 disables worker timeout so long-lived MCP server connections are never killed
# --keep-alive 300 keeps HTTP connections alive for 5 minutes to support persistent MCP sessions
# --worker-connections 1000 allows up to 1000 concurrent greenlet-based connections per worker
# --forwarded-allow-ips * ensures correct IP forwarding when behind a reverse proxy
ENTRYPOINT ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --timeout 0 --keep-alive 300 --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker --worker-connections 1000 --workers 1 --forwarded-allow-ips '*' oneshot.server:app"]
#ENTRYPOINT ["python", "-m", "oneshot.server"]