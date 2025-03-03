.PHONY: up down test shell build

# Start the application
up:
	docker compose up -d app

# Stop all services
down:
	docker compose down

# Run tests
test:
	docker compose exec app pytest /app/tests.py

# Get a shell in the running app container
shell:
	docker compose exec app /bin/bash

# Build all images
build:
	docker compose build
