# Deployment Guide: Rust Dataset Builder with Flyte

This guide walks you through deploying the Rust Dataset Builder with Flyte orchestration on your k3s cluster.

## Prerequisites

### 1. k3s Cluster Setup
Ensure your k3s cluster is running:
```bash
# Check cluster status
kubectl cluster-info
kubectl get nodes
```

### 2. Flyte Installation
Install Flyte on your k3s cluster:
```bash
# Add Flyte Helm repository
helm repo add flyteorg https://flyteorg.github.io/flyte
helm repo update

# Install Flyte
kubectl create namespace flyte-system
helm install flyte flyteorg/flyte-core -n flyte-system --values flyte-installation/onprem-flyte-binary-values.yaml
```

### 3. Required Tools
```bash
# Install required tools
pip install flytekit
docker login ghcr.io -u franck-sorel
```

## Quick Deployment

### Option 1: Automated Deployment
```bash
# Set your GitHub token
export GITHUB_TOKEN="your_github_token_here"

# Deploy everything
make flyte-deploy

# Register workflows
make flyte-register

# Run a workflow
make flyte-run
```

### Option 2: Manual Step-by-Step

#### Step 1: Build and Push Docker Image
```bash
# Build Flyte-compatible image
make flyte-build

# Push to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u franck-sorel --password-stdin
docker push ghcr.io/franck-sorel/rust-dataset-builder:latest
```

#### Step 2: Deploy to Kubernetes
```bash
# Update GitHub token in namespace.yaml
sed -i "s/YOUR_GITHUB_TOKEN_HERE/$GITHUB_TOKEN/g" k8s/namespace.yaml

# Apply Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml

# Wait for deployment
kubectl wait --for=condition=available --timeout=300s deployment/rust-dataset-builder -n rust-dataset-builder
```

#### Step 3: Register Workflows
```bash
cd flyte
pyflyte register --project rust-dataset --domain development workflows.py
```

#### Step 4: Run Workflows
```bash
# Prepare input data
cp sample_input.csv input.csv

# Run standard workflow
pyflyte run --remote workflows.py rust_dataset_extraction_workflow --input_csv ../input.csv

# Or run distributed workflow
pyflyte run --remote workflows.py distributed_rust_dataset_workflow --input_csv ../input.csv --parallel_workers 4
```

## Monitoring and Troubleshooting

### Check Deployment Status
```bash
# Check pods and services
kubectl get pods,svc,ingress -n rust-dataset-builder

# Check Flyte system
kubectl get pods -n flyte-system
```

### View Logs
```bash
# Application logs
kubectl logs -n rust-dataset-builder -l app=rust-dataset-builder --tail=100 -f

# Flyte admin logs
kubectl logs -n flyte-system -l app=flyte-admin --tail=100 -f
```

### Access Flyte Console
```bash
# Port forward to Flyte admin
kubectl port-forward -n flyte-system svc/flyte-admin 8080:80

# Open browser to http://localhost:8080
```

### Common Issues and Solutions

#### 1. Image Pull Errors
```bash
# Ensure you're logged into GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u franck-sorel --password-stdin

# Make repository public or add image pull secrets
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=franck-sorel \
  --docker-password=$GITHUB_TOKEN \
  -n rust-dataset-builder
```

#### 2. Workflow Registration Issues
```bash
# Check Flyte admin connectivity
kubectl port-forward -n flyte-system svc/flyte-admin 8081:81

# Update flyte.yaml with correct endpoint
export FLYTE_PLATFORM_URL=http://localhost:8081
```

#### 3. Resource Constraints
```bash
# Check node resources
kubectl top nodes
kubectl describe nodes

# Adjust resource requests in k8s/deployment.yaml if needed
```

## Workflow Configuration

### Resource Limits
Adjust resources in [`k8s/deployment.yaml`](k8s/deployment.yaml):
```yaml
resources:
  requests:
    cpu: 1000m      # 1 CPU core
    memory: 2Gi     # 2GB RAM
  limits:
    cpu: 4000m      # 4 CPU cores
    memory: 8Gi     # 8GB RAM
```

### Parallel Processing
Configure parallel workers in the workflow:
```python
# In flyte/workflows.py
distributed_rust_dataset_workflow(
    input_csv=input_csv,
    parallel_workers=4  # Adjust based on cluster capacity
)
```

### Storage Configuration
Update MinIO settings in [`flyte/flyte.yaml`](flyte/flyte.yaml):
```yaml
storage:
  type: minio
  connection:
    endpoint: http://minio.flyte-system.svc.cluster.local:9000
    access-key: minio
    secret-key: miniostorage
```

## Data Flow

```
Input CSV → Filter → Clone → Analyze → Collect → Output Files
    ↓         ↓       ↓       ↓         ↓         ↓
  Flyte    Flyte   Flyte   Flyte     Flyte    MinIO
  Task     Task    Task    Task      Task     Storage
```

## Performance Tuning

### For Large Datasets (1000+ repositories):
1. **Increase parallel workers**: Set `parallel_workers=8` or higher
2. **Adjust timeouts**: Increase `analysis_timeout` in configuration
3. **Scale cluster**: Add more k3s nodes for distributed processing
4. **Optimize storage**: Use faster storage classes for MinIO

### For Resource-Constrained Environments:
1. **Reduce parallel workers**: Set `parallel_workers=2`
2. **Lower resource limits**: Adjust CPU/memory in deployment
3. **Process in batches**: Split large CSV files into smaller chunks

## Security Considerations

1. **GitHub Token**: Store securely in Kubernetes secrets
2. **Image Registry**: Use private registry for production
3. **Network Policies**: Implement network segmentation
4. **RBAC**: Configure appropriate service account permissions

## Backup and Recovery

### Backup Workflow Results
```bash
# Export workflow outputs
kubectl exec -n rust-dataset-builder deployment/rust-dataset-builder -- \
  tar -czf /tmp/results.tar.gz /tmp/flyte-outputs/

# Copy to local machine
kubectl cp rust-dataset-builder/rust-dataset-builder-xxx:/tmp/results.tar.gz ./results.tar.gz
```

### Disaster Recovery
```bash
# Backup Flyte metadata
kubectl get configmaps,secrets -n flyte-system -o yaml > flyte-backup.yaml

# Restore if needed
kubectl apply -f flyte-backup.yaml
```

## Next Steps

1. **Scale Up**: Add more k3s nodes for larger workloads
2. **Monitoring**: Integrate with Prometheus/Grafana
3. **CI/CD**: Set up automated deployment pipelines
4. **Data Pipeline**: Connect to downstream ML training systems

For support, check the [main README](README.md) or open an issue on GitHub.