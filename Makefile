# Alpha Machine - Service Control Center
# ========================================
# Use this Makefile to manage and run independent services using a shared
# virtual environment powered by uv.
#
# Example: make install
#          make run service=linear
#          make run-dev
#          make test-transcript-linear

.PHONY: help install run run-dev test-transcript-linear stop build

# Define services and their ports
SERVICES := linear notion slackbot transcript
LINEAR_PORT := 8002
NOTION_PORT := 8003
SLACKBOT_PORT := 8001
TRANSCRIPT_PORT := 8000

help:
	@echo "ALPHA MACHINE SERVICE CONTROL"
	@echo "--------------------------------"
	@echo "Usage: make <command> [service=<service_name>]"
	@echo ""
	@echo "COMMANDS:"
	@echo "  install            - Create a shared venv and install all dependencies"
	@echo "  run                - Run a specific service in the foreground (e.g., make run service=linear)"
	@echo "  run-dev            - Run all services in the background"
	@echo "  test-transcript-linear - Run the end-to-end test for the transcript and linear services"
	@echo "  stop               - Stop all background services started with run-dev"
	@echo "  build              - Build a Docker image for a specific service (e.g., make build service=notion)"
	@echo ""
	@echo "AVAILABLE SERVICES:"
	@echo "  $(SERVICES)"
	@echo ""

# Check if service is defined
define check_service
  $(if $(filter $(service),$(SERVICES)),,$(error Invalid service name '$(service)'. Available services: $(SERVICES)))
endef

# Install all workspace dependencies into a single virtual environment
install:
	@echo "--- Creating shared virtual environment and installing all dependencies ---"
	@uv venv
	@uv pip install -e services/linear -e services/notion -e services/slackbot -e services/transcript -e shared/core -e shared/services
	@uv pip install requests

# Run a specific service
run:
	@$(call check_service)
	@echo "--- Running $(service) service ---"
	@$(eval SERVICE_UPPER := $(shell echo $(service) | tr 'a-z' 'A-Z'))
	@uv run uvicorn services.$(service).main:app --host 0.0.0.0 --port $($(SERVICE_UPPER)_PORT) --reload

# Run all services in the background
run-dev:
	@echo "--- Starting all services for development ---"
	@echo "--- Starting linear service on port $(LINEAR_PORT) ---"
	@(uv run uvicorn services.linear.main:app --host 0.0.0.0 --port $(LINEAR_PORT) --reload &> /tmp/alpha-machine-linear.log &)
	@echo "--- Starting notion service on port $(NOTION_PORT) ---"
	@(uv run uvicorn services.notion.main:app --host 0.0.0.0 --port $(NOTION_PORT) --reload &> /tmp/alpha-machine-notion.log &)
	@echo "--- Starting slackbot service on port $(SLACKBOT_PORT) ---"
	@(uv run uvicorn services.slackbot.main:app --host 0.0.0.0 --port $(SLACKBOT_PORT) --reload &> /tmp/alpha-machine-slackbot.log &)
	@echo "--- Starting transcript service on port $(TRANSCRIPT_PORT) ---"
	@(uv run uvicorn services.transcript.main:app --host 0.0.0.0 --port $(TRANSCRIPT_PORT) --reload &> /tmp/alpha-machine-transcript.log &)
	@sleep 2 # Give services a moment to start
	@echo "--- All services started in the background. Logs are in /tmp/ ---"

# Run the transcript-linear integration test
test-transcript-linear:
	@echo "--- Running Transcript -> Linear end-to-end test ---"
	@uv run python tests/test_transcript_linear_flow.py

# Stop all background services
stop:
	@echo "--- Stopping all background services ---"
	@pkill -f "uvicorn services.*.main:app" || true
	@echo "--- All services stopped ---"

# Build a Docker image for a specific service
build:
	@$(call check_service)
	@echo "--- Building Docker image for $(service) service ---"
	@docker build -t alpha-machine-$(service) -f services/$(service)/Dockerfile . 