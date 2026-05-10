FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.12 /uv /uvx /usr/local/bin/

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Step 1: install dependencies only — layer is cached until lockfile changes
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Step 2: copy source, then install the project wheel
COPY src/ ./src/
RUN uv sync --frozen --no-dev --no-editable

# Non-root user
RUN useradd --system --no-create-home etfmcp
USER etfmcp

EXPOSE 8765

CMD ["/app/.venv/bin/python", "-m", "etf_mcp"]
