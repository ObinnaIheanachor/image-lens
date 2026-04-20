.PHONY: demo-lite demo run warm

demo-lite:
	docker compose -f docker-compose.lite.yml up --build

demo:
	docker compose up --build

run:
	uvicorn src.main:app --reload

warm:
	docker pull python:3.11-slim
	docker pull postgres:16-alpine
	docker pull redis:7-alpine
	docker pull minio/minio:latest
	docker pull mendhak/http-https-echo:35
