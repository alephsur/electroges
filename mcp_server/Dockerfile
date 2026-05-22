FROM python:3.12-slim

WORKDIR /app

RUN pip install uv --no-cache-dir

COPY pyproject.toml .
RUN uv sync --no-dev

COPY . .

ENV PYTHONPATH=/app
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8080

EXPOSE 8080

CMD ["uv", "run", "python", "main.py"]
