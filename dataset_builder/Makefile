# Rust Dataset Builder Makefile

.PHONY: help build run test clean docker-build docker-run docker-clean install-tools flyte-build flyte-deploy flyte-register flyte-run flyte-clean

# Default target
help:
	@echo "Available targets:"
	@echo "  build         - Build the Rust application"
	@echo "  run           - Run the application with sample data"
	@echo "  test          - Run tests"
	@echo "  clean         - Clean build artifacts"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Run with Docker Compose"
	@echo "  docker-clean  - Clean Docker resources"
	@echo "  install-tools - Install required analysis tools"
	@echo ""
	@echo "Flyte targets:"
	@echo "  flyte-build   - Build Flyte-compatible Docker image"
	@echo "  flyte-deploy  - Deploy to k3s with Flyte"
	@echo "  flyte-register- Register workflows with Flyte"
	@echo "  flyte-run     - Run workflow on Flyte"
	@echo "  flyte-clean   - Clean Flyte deployment"

# Build the application
build:
	cargo build --release

# Run with sample data (requires GITHUB_TOKEN)
run:
	@if [ -z "$(GITHUB_TOKEN)" ]; then \
		echo "Error: GITHUB_TOKEN environment variable is required"; \
		echo "Set it with: export GITHUB_TOKEN=your_token_here"; \
		exit 1; \
	fi
	cp sample_input.csv input.csv
	cargo run --release -- $(GITHUB_TOKEN) full

# Run tests
test:
	cargo test

# Clean build artifacts
clean:
	cargo clean
	rm -rf datasets/
	rm -f filtered_repos.txt outputs.jsonl code.jsonl input.csv

# Docker targets
docker-build:
	docker build -t dataset-builder .

docker-run:
	@if [ -z "$(GITHUB_TOKEN)" ]; then \
		echo "Error: GITHUB_TOKEN environment variable is required"; \
		echo "Set it with: export GITHUB_TOKEN=your_token_here"; \
		exit 1; \
	fi
	mkdir -p data
	cp sample_input.csv input.csv
	docker-compose up dataset-builder

docker-clean:
	docker-compose down
	docker rmi dataset-builder:latest 2>/dev/null || true

# Install required analysis tools
install-tools:
	@echo "Installing Rust analysis tools..."
	cargo install cargo-audit cargo-deny cargo-geiger cargo-auditable
	@echo "Installing Python tools..."
	pip3 install semgrep
	@echo "Tools installed successfully!"

# Development targets
dev-run:
	cp sample_input.csv input.csv
	cargo run -- dummy-token full

check:
	cargo check
	cargo clippy
	cargo fmt --check

format:
	cargo fmt

# Flyte targets
flyte-build:
	@echo "Building Flyte-compatible Docker image..."
	docker build -f Dockerfile.flyte -t ghcr.io/franck-sorel/rust-dataset-builder:latest .

flyte-deploy:
	@echo "Deploying to k3s with Flyte..."
	@if [ -z "$(GITHUB_TOKEN)" ]; then \
		echo "Error: GITHUB_TOKEN environment variable is required"; \
		echo "Set it with: export GITHUB_TOKEN=your_token_here"; \
		exit 1; \
	fi
	./scripts/deploy-flyte.sh

flyte-register:
	@echo "Registering workflows with Flyte..."
	cd flyte && pyflyte register --project rust-dataset --domain development workflows.py

flyte-run:
	@echo "Running workflow on Flyte..."
	@if [ ! -f "input.csv" ]; then \
		echo "Creating sample input.csv..."; \
		cp sample_input.csv input.csv; \
	fi
	cd flyte && pyflyte run --remote workflows.py rust_dataset_extraction_workflow --input_csv ../input.csv

flyte-run-distributed:
	@echo "Running distributed workflow on Flyte..."
	@if [ ! -f "input.csv" ]; then \
		echo "Creating sample input.csv..."; \
		cp sample_input.csv input.csv; \
	fi
	cd flyte && pyflyte run --remote workflows.py distributed_rust_dataset_workflow --input_csv ../input.csv --parallel_workers 4

flyte-clean:
	@echo "Cleaning Flyte deployment..."
	kubectl delete namespace rust-dataset-builder --ignore-not-found=true
	docker rmi ghcr.io/franck-sorel/rust-dataset-builder:latest 2>/dev/null || true

flyte-logs:
	@echo "Showing Flyte deployment logs..."
	kubectl logs -n rust-dataset-builder -l app=rust-dataset-builder --tail=100 -f

flyte-status:
	@echo "Checking Flyte deployment status..."
	kubectl get pods,svc,ingress -n rust-dataset-builder

# Development workflow with Flyte
dev-flyte: flyte-build flyte-deploy flyte-register
	@echo "Development environment ready!"
	@echo "Run 'make flyte-run' to execute a workflow"