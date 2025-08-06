# Use Python slim image with uv for fast dependency management
FROM python:3.13-slim

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set the working directory
WORKDIR /workspace

# Copy the entire workspace (monorepo structure)
COPY . .

# Install dependencies using uv with frozen lockfile
RUN uv sync --frozen

# Expose the service port
EXPOSE 8003

# Run the service using uv
CMD ["uv", "run", "uvicorn", "services.notion.main:app", "--host", "0.0.0.0", "--port", "8003"] 