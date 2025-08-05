# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /workspace

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy the entire workspace (this preserves the workspace structure)
COPY . .

# Install the slackbot service and its workspace dependencies using uv
RUN uv sync --frozen

# Make port 8001 available to the world outside this container
EXPOSE 8001

# Run main.py from workspace root where shared imports work
CMD ["uv", "run", "uvicorn", "services.slackbot.main:app", "--host", "0.0.0.0", "--port", "8001"] 