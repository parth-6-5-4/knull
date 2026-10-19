.PHONY: install dev test eval ui clean

# Install dependencies
install:
	pip install -r requirements.txt

# Run development server
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Console UI (React + TypeScript): dev server / production build
ui:
	cd web && npm install && npm run dev

ui-build:
	cd web && npm install && npm run build

# Run tests
test:
	pytest tests/ -v --cov=app --cov-report=term-missing

# Run evaluation
eval:
	python eval/run_eval.py

# Setup Ollama model
ollama-setup:
	ollama pull llama3.2:3b

# Clean generated files
clean:
	rm -rf chroma_data app_data __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Create data directories
dirs:
	mkdir -p chroma_data app_data

# Full setup
setup: install dirs ollama-setup
	@echo "Setup complete! Run 'make dev' to start the server."
