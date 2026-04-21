.PHONY: demo-lite demo run warm lint typecheck test migrate-up migrate-current

demo-lite:
	docker compose -f docker-compose.lite.yml up --build

demo:
	docker compose up --build

run:
	uvicorn src.main:app --reload

lint:
	ruff check .

typecheck:
	mypy src

test:
	pytest -q tests

migrate-up:
	alembic upgrade head

migrate-current:
	alembic current

warm:
	docker pull python:3.11-slim
	docker pull postgres:16-alpine
	docker pull redis:7-alpine
	docker pull minio/minio:latest
	docker pull mendhak/http-https-echo:35
	docker pull node:20-alpine
