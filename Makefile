.PHONY: build run stats

# Default generator type if not provided
GENERATOR ?= wand

build:
	@echo "Building Docker image..."
	docker compose build

run:
	@echo "Running container with generator type: $(GENERATOR)..."
	docker compose run --rm app --generator-type=$(GENERATOR)

run-all:
	docker compose run --rm app --generator-type=wand
	docker compose run --rm app --generator-type=pdf2image
	docker compose run --rm app --generator-type=fitz
	docker compose run --rm app --generator-type=pypdfium2
	docker compose run --rm app --generator-type=pyvips

stats:
	@echo "Collecting statistics for generator type: $(GENERATOR)..."
	@docker compose run --rm app --generator-type=$(GENERATOR) 2>&1 | grep "seconds"

help:
	@echo "Usage: make [target] [GENERATOR=generator_type]"
	@echo "Targets:"
	@echo "  build          Build the Docker image"
	@echo "  run            Run the container with the specified generator type (default: wand)"
	@echo "  stats          Run the container and collect statistics for the specified generator type"
	@echo "  help           Show this help message"
	@echo ""
	@echo "Example:"
	@echo "  make run GENERATOR=fitz"
	@echo "  make stats GENERATOR=pyvips"
