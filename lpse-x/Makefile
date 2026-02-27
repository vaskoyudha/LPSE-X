.PHONY: install install-frontend start test build-frontend

install:
	python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

start:
	python -m uvicorn backend.main:app --reload

test:
	python -m pytest tests/ -q

build-frontend:
	cd frontend && npm run build
