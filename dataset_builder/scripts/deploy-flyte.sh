#!/bin/bash

# Deployment script for Rust Dataset Builder on k3s with Flyte
set -e

echo "🚀 Deploying Rust Dataset Builder to k3s with Flyte..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster"
    echo "Make sure your k3s cluster is running and kubectl is configured"
    exit 1
fi

# Check if Flyte is installed
if ! kubectl get namespace flyte &> /dev/null; then
    echo "❌ Flyte system namespace not found"
    echo "Please install Flyte first: https://docs.flyte.org/en/latest/deployment/index.html"
    exit 1
fi

# Prompt for GitHub token if not set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "📝 GitHub token not found in environment"
    read -s -p "Enter your GitHub token: " GITHUB_TOKEN
    echo
fi

# Validate GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GitHub token is required"
    exit 1
fi

echo "🔧 Building and pushing Docker image..."

# Build the Flyte-compatible Docker image
docker build -f Dockerfile.flyte -t ghcr.io/registry072/rust-dataset-builder:latest .

# Push to GitHub Container Registry
echo "📦 Pushing image to GitHub Container Registry..."
echo $GITHUB_TOKEN | docker login ghcr.io -u registry072 --password-stdin
docker push ghcr.io/registry072/rust-dataset-builder:latest

echo "🔐 Creating Kubernetes secrets..."

# Update the GitHub token in the namespace manifest
sed -i.bak "s/YOUR_GITHUB_TOKEN_HERE/$GITHUB_TOKEN/g" k8s/namespace.yaml

echo "🚀 Deploying to Kubernetes..."

# Apply Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/rust-dataset-builder -n rust-dataset-builder

# Get service information
echo "✅ Deployment completed successfully!"
echo
echo "📊 Service Information:"
kubectl get pods,svc,ingress -n rust-dataset-builder

echo
echo "🔗 Access Information:"
echo "- Service: rust-dataset-builder-service.rust-dataset-builder.svc.cluster.local"
echo "- Ingress: http://rust-dataset-builder.local (add to /etc/hosts if needed)"
echo
echo "📋 Next Steps:"
echo "1. Register workflows with Flyte:"
echo "   pyflyte register --project rust-dataset --domain development flyte/workflows.py"
echo
echo "2. Run a workflow:"
echo "   pyflyte run --remote flyte/workflows.py rust_dataset_extraction_workflow --input_csv /path/to/input.csv"
echo
echo "3. Monitor workflows in Flyte Console:"
echo "   kubectl port-forward -n flyte-system svc/flyte-admin 8080:80"
echo "   Open http://localhost:8080"

# Restore original namespace.yaml
mv k8s/namespace.yaml.bak k8s/namespace.yaml 2>/dev/null || true

echo "🎉 Deployment complete!"