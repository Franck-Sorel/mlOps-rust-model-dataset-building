# Project Structure

```
dataset_builder/
├── src/
│   └── main.rs                 # Main Rust application with CLI and pipeline logic
├── flyte/
│   ├── workflows.py            # Flyte workflow definitions
│   ├── requirements.txt        # Python dependencies for Flyte
│   └── flyte.yaml             # Flyte configuration
├── k8s/
│   ├── namespace.yaml          # Kubernetes namespace and secrets
│   └── deployment.yaml         # Kubernetes deployment, service, and ingress
├── scripts/
│   └── deploy-flyte.sh         # Automated deployment script
├── Cargo.toml                  # Rust dependencies and project metadata
├── Cargo.lock                  # Locked dependency versions
├── Dockerfile                  # Standard Docker image
├── Dockerfile.flyte            # Flyte-compatible Docker image
├── docker-compose.yml          # Docker Compose configuration
├── .dockerignore              # Docker build exclusions
├── .env.example               # Environment variable template
├── .gitignore                 # Git exclusions
├── Makefile                   # Build and deployment automation
├── README.md                  # Main project documentation
├── DEPLOYMENT.md              # Detailed deployment guide
├── PROJECT_STRUCTURE.md       # This file
└── sample_input.csv           # Example input data
```

## Key Components

### Core Application (`src/main.rs`)
- **CLI Interface**: Built with `clap` for command-line operations
- **Pipeline Commands**: `filter`, `clone`, `outputs`, `collect`, `full`
- **Analysis Tools**: Integration with cargo tools and external SAST tools
- **Error Handling**: Comprehensive error handling with `anyhow`

### Flyte Workflows (`flyte/workflows.py`)
- **Task Definitions**: Individual steps as Flyte tasks
- **Workflow Orchestration**: Sequential and distributed processing
- **Resource Management**: CPU/memory limits and requests
- **Secret Management**: Secure GitHub token handling

### Kubernetes Deployment (`k8s/`)
- **Namespace**: Isolated environment for the application
- **Secrets**: Secure storage for GitHub tokens
- **Deployment**: Scalable pod management
- **Service**: Internal cluster networking


### Docker Images
- **Standard Docker**: For local development and testing
- **Flyte Docker**: Optimized for Flyte workflow execution
- **Multi-stage Build**: Efficient image size and build caching

### Automation (`Makefile` & `scripts/`)
- **Build Targets**: Rust compilation and Docker image building
- **Deployment**: Automated k3s deployment with Flyte
- **Workflow Management**: Registration and execution commands
- **Development**: Local testing and debugging helpers

## Data Flow

1. **Input**: CSV file with repository metadata
2. **Filter**: Extract repositories with Cargo.toml and Cargo.lock
3. **Clone**: Download repositories from GitHub
4. **Analyze**: Run static analysis tools (clippy, audit, semgrep, etc.)
5. **Collect**: Extract source code files
6. **Output**: Generate JSONL files for ML training

## Scalability Features

- **Distributed Processing**: Parallel execution across multiple workers
- **Resource Scaling**: Configurable CPU/memory limits
- **Fault Tolerance**: Automatic retry and error recovery
- **Data Lineage**: Complete tracking of data transformations
- **Monitoring**: Built-in metrics and logging

## Integration Points

- **Flyte**: Workflow orchestration and monitoring
- **Kubernetes**: Container orchestration and scaling
- **MinIO**: Object storage for intermediate and final results
- **GitHub**: Source code repository access
- **Container Registry**: Docker image distribution

This architecture supports both small-scale development and large-scale production deployments for creating comprehensive Rust code datasets.