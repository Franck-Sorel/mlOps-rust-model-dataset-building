# Rust Dataset Builder

A comprehensive tool for extracting and analyzing Rust code repositories to create training datasets for AI models. Includes Flyte workflow orchestration for scalable, distributed processing on Kubernetes.

## Features

- **Filter**: Extract repositories with both `Cargo.toml` and `Cargo.lock` files
- **Clone**: Shallow clone GitHub repositories with authentication
- **Analyze**: Run 10+ static analysis and security tools on each repository
- **Collect**: Extract all source code files from repositories
- **Full Pipeline**: Execute the complete workflow end-to-end

## Quick Start with Docker

### Prerequisites

1. **GitHub Token**: Create a personal access token at GitHub Settings → Developer settings → Personal access tokens
2. **Input CSV**: Prepare a CSV file with columns: `id,name,has_toml,has_lock`

### Using Docker Compose (Recommended)

1. **Set up your environment**:
   ```bash
   # Create data directory
   mkdir -p data
   
   # Set your GitHub token
   export GITHUB_TOKEN="your_github_token_here"
   
   # Place your input CSV file
   cp your_repos.csv input.csv
   ```

2. **Run the full pipeline**:
   ```bash
   docker-compose up dataset-builder
   ```

3. **For interactive use**:
   ```bash
   # Start interactive container
   docker-compose up -d dataset-builder-interactive
   
   # Execute commands
   docker-compose exec dataset-builder-interactive dataset_builder $GITHUB_TOKEN filter input.csv filtered_repos.txt
   docker-compose exec dataset-builder-interactive dataset_builder $GITHUB_TOKEN clone filtered_repos.txt datasets
   docker-compose exec dataset-builder-interactive dataset_builder $GITHUB_TOKEN outputs datasets outputs.jsonl
   docker-compose exec dataset-builder-interactive dataset_builder $GITHUB_TOKEN collect datasets code.jsonl
   ```

### Using Docker Directly

1. **Build the image**:
   ```bash
   docker build -t dataset-builder .
   ```

2. **Run with volume mounts**:
   ```bash
   docker run -it --rm \
     -v $(pwd)/data:/data \
     -v $(pwd)/input.csv:/data/input.csv:ro \
     -e GITHUB_TOKEN="your_token_here" \
     dataset-builder your_token_here full
   ```

## Local Development

### Prerequisites

- Rust 1.75+
- Git
- Python 3 (for external tools)

### Install Analysis Tools

```bash
# Rust tools
cargo install cargo-audit cargo-deny cargo-geiger cargo-auditable

# External tools
pip install semgrep

# Optional: CodeQL (large download)
# Download from: https://github.com/github/codeql-cli-binaries/releases
```

### Build and Run

```bash
# Build
cargo build --release

# Run full pipeline
export GITHUB_TOKEN="your_token_here"
cargo run --release -- $GITHUB_TOKEN full

# Run individual commands
cargo run --release -- $GITHUB_TOKEN filter input.csv filtered_repos.txt
cargo run --release -- $GITHUB_TOKEN clone filtered_repos.txt datasets
cargo run --release -- $GITHUB_TOKEN outputs datasets outputs.jsonl
cargo run --release -- $GITHUB_TOKEN collect datasets code.jsonl
```

## Commands

### `filter <csv> <out>`
Filters repositories from CSV input, keeping only those with both Cargo.toml and Cargo.lock files.

**Input CSV format**:
```csv
id,name,has_toml,has_lock
1,rust-lang/rust,true,true
2,tokio-rs/tokio,true,true
```

### `clone <names> <out>`
Clones repositories listed in the names file to the output directory.

### `outputs <root> <outputs>`
Runs analysis tools on all repositories in the root directory and saves results to JSONL file.

**Analysis tools included**:
- `cargo clippy` - Linting
- `cargo fmt --check` - Formatting
- `cargo audit` - Security vulnerabilities
- `cargo auditable` - Supply chain security
- `cargo deny check` - License and security policies
- `cargo geiger` - Unsafe code detection
- `cargo tree` - Dependency tree
- `rustc --emit=ast` - AST generation
- `semgrep` - Static analysis
- `codeql` - Security analysis (optional)

### `collect <root> <code>`
Collects all source code files from repositories and saves to JSONL file.

### `full`
Executes the complete pipeline: filter → clone → outputs → collect

## Output Files

### `outputs.jsonl`
Contains analysis results for each repository:
```json
{
  "name": "repo_name",
  "clippy": "clippy output...",
  "fmt": "fmt output...",
  "audit": "audit output...",
  "time_ms": {
    "clippy": 5230,
    "fmt": 180,
    "audit": 1200
  }
}
```

### `code.jsonl`
Contains source code files:
```json
{
  "name": "repo_name",
  "path": "src/main.rs",
  "content": "fn main() { ... }"
}
```

## Environment Variables

- `GITHUB_TOKEN`: GitHub personal access token (required)
- `RUST_LOG`: Log level (default: info)
- `RUST_BACKTRACE`: Enable backtraces (default: 1)

## Docker Image Details

The Docker image includes:
- Rust toolchain with analysis tools
- Python 3 with semgrep
- Git for repository operations
- All necessary system dependencies

**Image size**: ~2GB (includes full Rust toolchain and analysis tools)

## Use Cases

This tool is designed for:
- Creating training datasets for AI code models
- Large-scale Rust code analysis
- Security and quality assessment of Rust ecosystems
- Research on code patterns and quality metrics

## Flyte Workflow Orchestration

This project includes Flyte workflows for scalable, distributed processing on Kubernetes clusters.

### Prerequisites for Flyte

1. **k3s Kubernetes cluster** with Flyte installed
2. **GitHub Container Registry access** for image storage
3. **GitHub token** for repository access

### Flyte Setup

1. **Deploy to k3s with Flyte**:
   ```bash
   export GITHUB_TOKEN="your_github_token_here"
   make flyte-deploy
   ```

2. **Register workflows**:
   ```bash
   make flyte-register
   ```

3. **Run workflows**:
   ```bash
   # Standard workflow
   make flyte-run
   
   # Distributed workflow (4 parallel workers)
   make flyte-run-distributed
   ```

### Flyte Workflow Features

- **Scalable Processing**: Distributed analysis across multiple workers
- **Resource Management**: Configurable CPU/memory limits per task
- **Fault Tolerance**: Automatic retry and error handling
- **Data Lineage**: Complete tracking of data flow and transformations
- **Monitoring**: Built-in metrics and logging via Flyte Console

### Available Workflows

1. **`rust_dataset_extraction_workflow`**: Standard sequential processing
2. **`distributed_rust_dataset_workflow`**: Parallel processing with configurable workers

### Monitoring and Management

```bash
# Check deployment status
make flyte-status

# View logs
make flyte-logs

# Access Flyte Console
kubectl port-forward -n flyte-system svc/flyte-admin 8080:80
# Open http://localhost:8080
```

### Flyte Configuration

The workflow configuration is in [`flyte/flyte.yaml`](flyte/flyte.yaml) and includes:
- Resource limits and requests
- Storage configuration (MinIO)
- Secret management for GitHub tokens
- Timeout and retry policies

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Input CSV     │───▶│  Flyte Workflow  │───▶│  Output Files   │
│                 │    │                  │    │                 │
│ - Repository    │    │ 1. Filter Repos  │    │ - outputs.jsonl │
│   metadata      │    │ 2. Clone Repos   │    │ - code.jsonl    │
│ - has_toml      │    │ 3. Run Analysis  │    │ - datasets/     │
│ - has_lock      │    │ 4. Collect Code  │    │ - statistics    │
└─────────────────┘    │ 5. Generate Stats│    └─────────────────┘
                       └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   k3s Cluster    │
                    │                  │
                    │ - Rust Analysis  │
                    │ - Code Collection│
                    │ - Data Storage   │
                    └──────────────────┘
```

## License

MIT License - see LICENSE file for details