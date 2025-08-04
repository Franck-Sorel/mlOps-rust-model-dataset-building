"""
Flyte workflow for Rust Dataset Builder Pipeline
Orchestrates the complete dataset extraction and analysis workflow
"""

import os
from typing import List, NamedTuple
from dataclasses import dataclass
from flytekit import task, workflow, Resources, ImageSpec, Secret
from flytekit.types.file import FlyteFile
from flytekit.types.directory import FlyteDirectory
from flytekitplugins.kfpytorch import PyTorch

# Custom image with Rust dataset builder
rust_image = ImageSpec(
    name="rust-dataset-builder",
    base_image="rust:1.82-slim",
    packages=["flytekit>=1.10.0"],
    registry="ghcr.io/registry072",
    python_version="3.11"
)

@dataclass
class DatasetConfig:
    """Configuration for dataset extraction"""
    github_token_secret: str = "github-token"
    input_csv_path: str = "input.csv"
    max_repos: int = 100
    analysis_timeout: int = 3600  # 1 hour


class PipelineResults(NamedTuple):
    """Results from the complete pipeline"""
    filtered_repos: FlyteFile
    outputs_jsonl: FlyteFile
    code_jsonl: FlyteFile
    datasets_dir: FlyteDirectory
    summary_stats: dict


@task(
    container_image=rust_image,
    requests=Resources(cpu="1", mem="2Gi"),
    limits=Resources(cpu="2", mem="4Gi"),
    secret_requests=[Secret(key="github-token", group="github")]
)
def filter_repositories(
    input_csv: FlyteFile,
    config: DatasetConfig
) -> FlyteFile:
    """
    Filter repositories that have both Cargo.toml and Cargo.lock files
    """
    import subprocess
    import tempfile
    import os
    
    # Download input CSV
    input_path = input_csv.download()
    
    # Create output file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        output_path = f.name
    
    # Get GitHub token from secret
    github_token = os.environ.get("FLYTE_SECRETS_DEFAULT_DIR", "") + "/github-token"
    if os.path.exists(github_token):
        with open(github_token, 'r') as f:
            token = f.read().strip()
    else:
        token = os.environ.get("GITHUB_TOKEN", "dummy-token")
    
    # Run filter command
    cmd = [
        "/usr/local/bin/dataset_builder",
        token,
        "filter",
        input_path,
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Filter command failed: {result.stderr}")
    
    return FlyteFile(path=output_path)


@task(
    container_image=rust_image,
    requests=Resources(cpu="2", mem="4Gi"),
    limits=Resources(cpu="4", mem="8Gi"),
    secret_requests=[Secret(key="github-token", group="github")]
)
def clone_repositories(
    filtered_repos: FlyteFile,
    config: DatasetConfig
) -> FlyteDirectory:
    """
    Clone filtered repositories from GitHub
    """
    import subprocess
    import tempfile
    import os
    
    # Download filtered repos list
    repos_path = filtered_repos.download()
    
    # Create output directory
    datasets_dir = tempfile.mkdtemp(prefix="datasets_")
    
    # Get GitHub token from secret
    github_token = os.environ.get("FLYTE_SECRETS_DEFAULT_DIR", "") + "/github-token"
    if os.path.exists(github_token):
        with open(github_token, 'r') as f:
            token = f.read().strip()
    else:
        token = os.environ.get("GITHUB_TOKEN", "dummy-token")
    
    # Run clone command
    cmd = [
        "/usr/local/bin/dataset_builder",
        token,
        "clone",
        repos_path,
        datasets_dir
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Clone command failed: {result.stderr}")
    
    return FlyteDirectory(path=datasets_dir)


@task(
    container_image=rust_image,
    requests=Resources(cpu="4", mem="8Gi"),
    limits=Resources(cpu="8", mem="16Gi"),
    timeout=3600  # 1 hour timeout for analysis
)
def analyze_repositories(
    datasets_dir: FlyteDirectory,
    config: DatasetConfig
) -> FlyteFile:
    """
    Run static analysis tools on all repositories
    """
    import subprocess
    import tempfile
    import os
    
    # Download datasets directory
    datasets_path = datasets_dir.download()
    
    # Create output file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        outputs_path = f.name
    
    # Get GitHub token (needed for some analysis tools)
    github_token = os.environ.get("FLYTE_SECRETS_DEFAULT_DIR", "") + "/github-token"
    if os.path.exists(github_token):
        with open(github_token, 'r') as f:
            token = f.read().strip()
    else:
        token = os.environ.get("GITHUB_TOKEN", "dummy-token")
    
    # Run outputs command
    cmd = [
        "/usr/local/bin/dataset_builder",
        token,
        "outputs",
        datasets_path,
        outputs_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Analysis command failed: {result.stderr}")
    
    return FlyteFile(path=outputs_path)


@task(
    container_image=rust_image,
    requests=Resources(cpu="2", mem="4Gi"),
    limits=Resources(cpu="4", mem="8Gi")
)
def collect_source_code(
    datasets_dir: FlyteDirectory,
    config: DatasetConfig
) -> FlyteFile:
    """
    Collect all source code files from repositories
    """
    import subprocess
    import tempfile
    import os
    
    # Download datasets directory
    datasets_path = datasets_dir.download()
    
    # Create output file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        code_path = f.name
    
    # Get GitHub token
    github_token = os.environ.get("FLYTE_SECRETS_DEFAULT_DIR", "") + "/github-token"
    if os.path.exists(github_token):
        with open(github_token, 'r') as f:
            token = f.read().strip()
    else:
        token = os.environ.get("GITHUB_TOKEN", "dummy-token")
    
    # Run collect command
    cmd = [
        "/usr/local/bin/dataset_builder",
        token,
        "collect",
        datasets_path,
        code_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Collect command failed: {result.stderr}")
    
    return FlyteFile(path=code_path)


@task(
    requests=Resources(cpu="1", mem="2Gi"),
    limits=Resources(cpu="2", mem="4Gi")
)
def generate_summary_stats(
    filtered_repos: FlyteFile,
    outputs_jsonl: FlyteFile,
    code_jsonl: FlyteFile
) -> dict:
    """
    Generate summary statistics from the pipeline results
    """
    import json
    
    stats = {
        "total_repos_filtered": 0,
        "total_analysis_entries": 0,
        "total_code_files": 0,
        "total_lines_of_code": 0,
        "analysis_tools_summary": {},
        "file_extensions": {}
    }
    
    # Count filtered repos
    repos_path = filtered_repos.download()
    with open(repos_path, 'r') as f:
        stats["total_repos_filtered"] = len(f.readlines())
    
    # Analyze outputs
    outputs_path = outputs_jsonl.download()
    with open(outputs_path, 'r') as f:
        for line in f:
            if line.strip():
                stats["total_analysis_entries"] += 1
                try:
                    entry = json.loads(line)
                    # Collect timing statistics
                    if "time_ms" in entry:
                        for tool, time_ms in entry["time_ms"].items():
                            if tool not in stats["analysis_tools_summary"]:
                                stats["analysis_tools_summary"][tool] = {
                                    "total_time_ms": 0,
                                    "count": 0,
                                    "avg_time_ms": 0
                                }
                            stats["analysis_tools_summary"][tool]["total_time_ms"] += time_ms
                            stats["analysis_tools_summary"][tool]["count"] += 1
                except json.JSONDecodeError:
                    continue
    
    # Calculate averages
    for tool in stats["analysis_tools_summary"]:
        tool_stats = stats["analysis_tools_summary"][tool]
        if tool_stats["count"] > 0:
            tool_stats["avg_time_ms"] = tool_stats["total_time_ms"] / tool_stats["count"]
    
    # Analyze code files
    code_path = code_jsonl.download()
    with open(code_path, 'r') as f:
        for line in f:
            if line.strip():
                stats["total_code_files"] += 1
                try:
                    entry = json.loads(line)
                    # Count lines of code
                    if "content" in entry:
                        stats["total_lines_of_code"] += len(entry["content"].split('\n'))
                    
                    # Count file extensions
                    if "path" in entry:
                        ext = entry["path"].split('.')[-1] if '.' in entry["path"] else "no_ext"
                        stats["file_extensions"][ext] = stats["file_extensions"].get(ext, 0) + 1
                except json.JSONDecodeError:
                    continue
    
    return stats


@workflow
def rust_dataset_extraction_workflow(
    input_csv: FlyteFile,
    config: DatasetConfig = DatasetConfig()
) -> PipelineResults:
    """
    Complete Rust dataset extraction and analysis workflow
    
    This workflow:
    1. Filters repositories based on Cargo.toml/Cargo.lock presence
    2. Clones filtered repositories from GitHub
    3. Runs comprehensive static analysis on each repository
    4. Collects all source code files
    5. Generates summary statistics
    
    Args:
        input_csv: CSV file with repository information
        config: Configuration for the dataset extraction
    
    Returns:
        PipelineResults containing all generated artifacts and statistics
    """
    
    # Step 1: Filter repositories
    filtered_repos = filter_repositories(input_csv=input_csv, config=config)
    
    # Step 2: Clone repositories
    datasets_dir = clone_repositories(filtered_repos=filtered_repos, config=config)
    
    # Step 3: Analyze repositories (parallel with code collection)
    outputs_jsonl = analyze_repositories(datasets_dir=datasets_dir, config=config)
    
    # Step 4: Collect source code (can run in parallel with analysis)
    code_jsonl = collect_source_code(datasets_dir=datasets_dir, config=config)
    
    # Step 5: Generate summary statistics
    summary_stats = generate_summary_stats(
        filtered_repos=filtered_repos,
        outputs_jsonl=outputs_jsonl,
        code_jsonl=code_jsonl
    )
    
    return PipelineResults(
        filtered_repos=filtered_repos,
        outputs_jsonl=outputs_jsonl,
        code_jsonl=code_jsonl,
        datasets_dir=datasets_dir,
        summary_stats=summary_stats
    )


# Alternative workflow for distributed processing
@workflow
def distributed_rust_dataset_workflow(
    input_csv: FlyteFile,
    config: DatasetConfig = DatasetConfig(),
    parallel_workers: int = 4
) -> PipelineResults:
    """
    Distributed version of the dataset extraction workflow
    Uses PyTorch distributed processing for large-scale analysis
    """
    
    # Step 1: Filter repositories
    filtered_repos = filter_repositories(input_csv=input_csv, config=config)
    
    # Step 2: Clone repositories
    datasets_dir = clone_repositories(filtered_repos=filtered_repos, config=config)
    
    # Step 3 & 4: Run analysis and collection in parallel using PyTorch distributed
    pytorch_config = PyTorch(num_workers=parallel_workers)
    
    with pytorch_config:
        outputs_jsonl = analyze_repositories(datasets_dir=datasets_dir, config=config)
        code_jsonl = collect_source_code(datasets_dir=datasets_dir, config=config)
    
    # Step 5: Generate summary statistics
    summary_stats = generate_summary_stats(
        filtered_repos=filtered_repos,
        outputs_jsonl=outputs_jsonl,
        code_jsonl=code_jsonl
    )
    
    return PipelineResults(
        filtered_repos=filtered_repos,
        outputs_jsonl=outputs_jsonl,
        code_jsonl=code_jsonl,
        datasets_dir=datasets_dir,
        summary_stats=summary_stats
    )


if __name__ == "__main__":
    # For local testing
    from flytekit.clis.sdk_in_container import pyflyte
    import sys
    
    # Run with: python workflows.py
    print("Rust Dataset Builder Flyte Workflows")
    print("Available workflows:")
    print("- rust_dataset_extraction_workflow")
    print("- distributed_rust_dataset_workflow")