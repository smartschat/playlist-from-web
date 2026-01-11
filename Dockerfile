# Stage 1: Build frontend
FROM node:20-slim AS frontend-builder

WORKDIR /frontend
COPY src/app/web/frontend/package*.json ./
RUN npm ci
COPY src/app/web/frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/

# Copy built frontend from stage 1
COPY --from=frontend-builder /frontend/dist ./src/app/web/frontend/dist

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8002

CMD ["uv", "run", "python", "-m", "app", "serve", "--host", "0.0.0.0", "--port", "8002"]
