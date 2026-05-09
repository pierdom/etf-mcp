FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Install dependencies (no editable install — production image)
RUN uv sync --frozen --no-dev --no-editable

# Copy source
COPY src/ ./src/

# Non-root user
RUN useradd --system --no-create-home etfmcp
USER etfmcp

EXPOSE 8765

CMD ["uv", "run", "--no-sync", "python", "-m", "etf_mcp"]
