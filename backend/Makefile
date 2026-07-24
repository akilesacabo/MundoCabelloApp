.PHONY: install run test lint migrate revision

install:
	pip install -r requirements/dev.txt

run:
	uvicorn src.main:app --reload

test:
	pytest

lint:
	ruff check --fix src tests && ruff format src tests

revision:
	alembic revision --autogenerate -m "$(m)"

migrate:
	alembic upgrade head
