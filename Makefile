.PHONY: demo-lite run warm

demo-lite:
	docker compose -f docker-compose.lite.yml up --build

run:
	uvicorn src.main:app --reload

warm:
	docker pull python:3.11-slim
