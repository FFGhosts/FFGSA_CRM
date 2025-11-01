# Makefile for PiCMS

.PHONY: help install run dev db-init db-migrate clean test lint format build docker-up docker-down docker-logs

# Default target
help:
	@echo "PiCMS - Raspberry Pi Content Management System"
	@echo ""
	@echo "Available targets:"
	@echo "  make install      - Install dependencies"
	@echo "  make run          - Run Flask development server"
	@echo "  make dev          - Run in development mode with debug"
	@echo "  make db-init      - Initialize database"
	@echo "  make clean        - Clean temporary files"
	@echo "  make lint         - Run code linting"
	@echo "  make format       - Format code with black"
	@echo "  make build        - Build Docker image"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"
	@echo "  make docker-logs  - View Docker logs"
	@echo "  make ssl-cert     - Generate self-signed SSL certificate"

# Install dependencies
install:
	pip install -r requirements.txt
	@echo "Dependencies installed successfully"

# Run Flask development server
run:
	python app.py

# Run in development mode
dev:
	FLASK_ENV=development FLASK_DEBUG=1 python app.py

# Initialize database
db-init:
	python init_db.py

# Clean temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	@echo "Cleaned temporary files"

# Run tests
test:
	pytest tests/ -v --cov=. --cov-report=html

# Run linting
lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Format code
format:
	black . --line-length 100
	isort .

# Build Docker image
build:
	docker build -t picms:latest .

# Start Docker containers
docker-up:
	docker-compose up -d
	@echo "Docker containers started"
	@echo "Access the application at http://localhost"

# Stop Docker containers
docker-down:
	docker-compose down
	@echo "Docker containers stopped"

# View Docker logs
docker-logs:
	docker-compose logs -f

# Generate self-signed SSL certificate
ssl-cert:
	mkdir -p ssl
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout ssl/key.pem \
		-out ssl/cert.pem \
		-subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
	@echo "Self-signed SSL certificate generated in ssl/"

# Create .env file from example
env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ".env file created from .env.example"; \
		echo "Please update .env with your configuration"; \
	else \
		echo ".env file already exists"; \
	fi

# Setup for development
setup: env install db-init
	@echo "Development environment setup complete"

# Setup for production (Docker)
setup-prod: env ssl-cert build docker-up
	@echo "Production environment setup complete"
	@echo "Waiting for services to start..."
	@sleep 10
	docker-compose exec web python init_db.py

# Backup database
backup:
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	if [ -f database.db ]; then \
		cp database.db backups/database_$$timestamp.db; \
		echo "Backup created: backups/database_$$timestamp.db"; \
	else \
		echo "No database file found"; \
	fi

# Restart services
restart:
	docker-compose restart

# View running containers
ps:
	docker-compose ps
