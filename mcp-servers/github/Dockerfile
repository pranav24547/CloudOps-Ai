FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir "mcp[cli]>=1.12,<2" httpx pydantic

COPY mcp-servers/github /app/

ENV PYTHONUNBUFFERED=1 \
    CLOUDOPS_MODE=demo \
    MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8102

EXPOSE 8102

CMD ["python", "server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8102"]
