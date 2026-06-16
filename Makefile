PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn

-include .env
export

DB_HOST ?= localhost
DB_PORT ?= 5432
DB_NAME ?= smart_student_assessment
DB_USER ?= postgres
PGPASSWORD ?= $(DB_PASSWORD)

.PHONY: help setup venv install run db-create db-init db-reset db-drop check clean

help:
	@echo "Available commands:"
	@echo "  make setup      Create venv, install dependencies, create DB, apply schema"
	@echo "  make venv       Create local Python virtual environment"
	@echo "  make install    Install Python dependencies"
	@echo "  make run        Run FastAPI server at http://127.0.0.1:8000"
	@echo "  make db-create  Create PostgreSQL database if missing"
	@echo "  make db-init    Apply schema.sql to the database"
	@echo "  make db-reset   Drop, recreate, and initialize database"
	@echo "  make check      Compile Python files"
	@echo "  make clean      Remove local cache files"

setup: venv install db-create db-init

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(UVICORN) main:app --reload --host 127.0.0.1 --port 8000

db-create:
	@if ! psql -h $(DB_HOST) -p $(DB_PORT) -U $(DB_USER) -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$(DB_NAME)'" | grep -q 1; then \
		createdb -h $(DB_HOST) -p $(DB_PORT) -U $(DB_USER) $(DB_NAME); \
	else \
		echo "Database $(DB_NAME) already exists"; \
	fi

db-init:
	psql -h $(DB_HOST) -p $(DB_PORT) -U $(DB_USER) -d $(DB_NAME) -f schema.sql

db-drop:
	dropdb --if-exists -h $(DB_HOST) -p $(DB_PORT) -U $(DB_USER) $(DB_NAME)

db-reset: db-drop db-create db-init

check:
	$(PYTHON) -m py_compile main.py auth.py db.py auth_service.py student_service.py assessment_service.py question_service.py submission_service.py answers_service.py evaluation_service.py results_service.py schemas.py dependencies.py router/*.py

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
