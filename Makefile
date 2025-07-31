# Alpha Machine Development Commands
.PHONY: help linear slackbot notion transcript

help:
	@echo "Available commands:"
	@echo "  make linear     - Start Linear service on port 8002"
	@echo "  make slackbot   - Start Slackbot service on port 8001"
	@echo "  make notion     - Start Notion service on port 8003"
	@echo "  make transcript - Start Transcript service on port 8004"

linear:
	PYTHONPATH=$(PWD) uv run --directory services/linear uvicorn main:app --host 0.0.0.0 --port 8002

slackbot:
	PYTHONPATH=$(PWD) uv run --directory services/slackbot uvicorn main:app --host 0.0.0.0 --port 8001

notion:
	PYTHONPATH=$(PWD) uv run --directory services/notion uvicorn main:app --host 0.0.0.0 --port 8003

transcript:
	PYTHONPATH=$(PWD) uv run --directory services/transcript uvicorn main:app --host 0.0.0.0 --port 8004 