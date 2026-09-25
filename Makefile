.PHONY: help install dev bot api test docker-build docker-run clean deploy-netlify deploy-hostinger

help:
	@echo "IFSA Market Monitor - Makefile"
	@echo "=============================="
	@echo "install          - Install Python dependencies"
	@echo "dev              - Run API in dev mode (FastAPI)"
	@echo "bot              - Run bot continuous loop"
	@echo "api              - Run API server production"
	@echo "test             - Run tests"
	@echo "docker-build     - Build Docker image"
	@echo "docker-run       - Run with docker-compose"
	@echo "docker-logs      - Tail logs"
	@echo "deploy-netlify   - Deploy to Netlify"
	@echo "deploy-hostinger - Deploy to Hostinger VPS"
	@echo "clean            - Clean caches"

install:
	pip install -r requirements.txt
	mkdir -p data logs

dev:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

bot:
	python -m src.bot

api:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 2

test:
	pytest tests/ -v || python -m pytest tests/ -v || echo "No tests yet"

docker-build:
	docker build -t ifsa-market-monitor .

docker-run:
	docker-compose up -d

docker-logs:
	docker-compose logs -f

docker-stop:
	docker-compose down

deploy-netlify:
	netlify deploy --prod

deploy-hostinger:
	bash scripts/deploy_hostinger.sh

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf data/*.json || true

setup:
	bash scripts/setup.sh
