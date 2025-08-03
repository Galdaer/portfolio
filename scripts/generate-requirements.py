#!/usr/bin/env python3
"""
Generate requirements.txt, requirements-ci.txt, and requirements-self-hosted.txt from requirements.in

This script generates three requirements files:
- requirements.txt: Full dependencies for local development and production
- requirements-ci.txt: Minimal dependencies for CI/CD validation (cloud runners)
- requirements-self-hosted.txt: GPU-optimized dependencies for self-hosted runners

Heavy GPU/ML packages are excluded from CI to improve build times and efficiency.
Self-hosted includes GPU packages but excludes development-only packages.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Packages that should be excluded from CI (GPU, heavy ML packages)
CI_EXCLUDED_PACKAGES = {
    # GPU/CUDA packages
    "torch",
    "nvidia-cublas-cu12",
    "nvidia-cuda-cupti-cu12",
    "nvidia-cuda-nvrtc-cu12",
    "nvidia-cuda-runtime-cu12",
    "nvidia-cudnn-cu12",
    "nvidia-cufft-cu12",
    "nvidia-cufile-cu12",
    "nvidia-curand-cu12",
    "nvidia-cusolver-cu12",
    "nvidia-cusparse-cu12",
    "nvidia-cusparselt-cu12",
    "nvidia-nccl-cu12",
    "nvidia-nvjitlink-cu12",
    "nvidia-nvtx-cu12",
    "triton",
    # Heavy ML/AI packages not needed for validation
    "unsloth",
    "unsloth-zoo",
    "accelerate",
    "bitsandbytes",
    "trl",
    "wandb",
    "datasets",
    "transformers",
    "peft",
    # Large data processing packages
    "matplotlib",
    "seaborn",
    "pandas",
    "scipy",
    "scikit-learn",
    "pillow",
    # Audio/video processing (if any)
    "ffmpeg",
    "opencv-python",
    # Development packages that aren't needed in CI
    "jupyter",
    "notebook",
    "ipython",
}

# Packages to exclude from self-hosted requirements (development/non-core packages only)
SELF_HOSTED_EXCLUDED_PACKAGES = {
    # Heavy ML packages that cause cache bloat - development only
    "unsloth",  # LoRA training - development only
    "transformers",  # Large model library - use specific models instead
    "datasets",  # Large dataset library - use specific datasets instead
    "peft",  # Parameter-efficient fine-tuning - development only
    "bitsandbytes",  # Quantization library - development only
    "accelerate",  # Multi-GPU training - development only
    "trl",  # Reinforcement learning - development only
    "wandb",  # Experiment tracking - development only
    # Pure development environments (NOT validation tools)
    "jupyter",  # Development environment
    "ipython",  # Interactive development
    "notebook",  # Jupyter notebooks
    "jupyterlab",  # Development IDE
    "ipykernel",  # Notebook kernel
    "ipywidgets",  # Interactive widgets
    # Git hooks (not needed in CI environments)
    "pre-commit",  # Git hooks
    # Documentation generation tools
    "sphinx",  # Documentation
    "mkdocs",  # Documentation
    # Data visualization packages (not needed for AI inference)
    "matplotlib",  # Plotting - not needed for AI inference
    "seaborn",  # Statistical plotting
    "plotly",  # Interactive plotting
    # Optional data science packages that can be loaded on-demand
    "pandas",  # Data manipulation - use specific operations
    "scikit-learn",  # Classical ML - use specific implementations
    # Coverage testing tools (basic pytest is enough for CI)
    "pytest-cov",  # Coverage testing
}

# Core packages that CI validation DOES need
CI_REQUIRED_PACKAGES = {
    # Web framework and API
    "flask",
    "fastapi",
    "uvicorn",
    "pydantic",
    "pydantic-settings",
    "starlette",
    # Database and storage
    "sqlalchemy",
    "alembic",
    "redis",
    "asyncpg",
    "psycopg2-binary",
    # HTTP clients and async
    "httpx",
    "aiofiles",
    "requests",
    # Authentication and security
    "python-multipart",
    "python-jose",
    "pyjwt",
    "passlib",
    "bcrypt",
    "cryptography",
    # Configuration
    "python-dotenv",
    "pyyaml",
    "jinja2",
    # Testing and validation
    "pytest",
    "pytest-asyncio",
    "ruff",
    "pyright",
    "yamllint",
    "pylint",
    # Healthcare-specific
    "fastmcp",
    "presidio-analyzer",
    "presidio-anonymizer",
    "structlog",
    # Core AI (lightweight)
    "langchain",
    "langgraph",
    "chromadb",
    "qdrant-client",
    "faiss-cpu",
    # Monitoring
    "prometheus-client",
    # Type stubs
    "types-requests",
}


def run_command(cmd: str, cwd: str | None = None) -> str | None:
    """Run a command and return the result stdout as string, or None on failure"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        if result.returncode != 0:
            print(f"Error running command: {cmd}")
            print(f"stderr: {result.stderr}")
            return None
        return result.stdout.strip()
    except Exception as e:
        print(f"Exception running command: {cmd} - {e}")
        return None


def create_ci_requirements_in(requirements_in_path: str) -> str:
    """Create a filtered requirements.in for CI by excluding heavy packages"""
    with open(requirements_in_path) as f:
        lines = f.readlines()

    filtered_lines = []

    for line in lines:
        line_stripped = line.strip()

        # Skip comments and empty lines
        if not line_stripped or line_stripped.startswith("#"):
            filtered_lines.append(line)
            continue

        # Check if this line contains a package we want to exclude
        # Handle various package specification formats:
        # - package==1.0.0
        # - package[extras]>=1.0.0
        # - package @ git+https://...
        # - package[extras] @ git+https://...
        package_name = (
            line_stripped.split("@")[0]  # Remove git URLs first
            .split(">=")[0]  # Remove version constraints
            .split("==")[0]  # Remove exact versions
            .split("[")[0]  # Remove extras specifications
            .strip()  # Clean whitespace
        )

        if package_name in CI_EXCLUDED_PACKAGES:
            print(f"Excluding from CI: {package_name}")
            continue

        filtered_lines.append(line)

    return "".join(filtered_lines)


def create_self_hosted_requirements_in(requirements_in_path: str) -> str:
    """Create a filtered requirements.in for self-hosted runners by excluding dev-only packages"""
    with open(requirements_in_path) as f:
        lines = f.readlines()

    filtered_lines = []

    for line in lines:
        line_stripped = line.strip()

        # Skip comments and empty lines
        if not line_stripped or line_stripped.startswith("#"):
            filtered_lines.append(line)
            continue

        # Check if this line contains a package we want to exclude
        # Handle various package specification formats:
        # - package==1.0.0
        # - package[extras]>=1.0.0
        # - package @ git+https://...
        # - package[extras] @ git+https://...
        package_name = (
            line_stripped.split("@")[0]  # Remove git URLs first
            .split(">=")[0]  # Remove version constraints
            .split("==")[0]  # Remove exact versions
            .split("[")[0]  # Remove extras specifications
            .strip()  # Clean whitespace
        )

        if package_name in SELF_HOSTED_EXCLUDED_PACKAGES:
            print(f"Excluding from self-hosted: {package_name}")
            continue

        filtered_lines.append(line)

    return "".join(filtered_lines)


def clean_requirements_content(content: str) -> str:
    """Clean up pip-compile generated content by removing via comments and temp paths"""
    lines = content.splitlines()
    cleaned_lines = []

    for line in lines:
        # Skip auto-generated header lines that reference temp files
        if line.startswith("#    uv pip compile") and "/tmp/" in line:
            continue
        # Skip "via" comment lines that clutter the output
        if line.strip().startswith("# via") and not line.strip().startswith("# via -r"):
            continue
        # Skip lines that are just "# via" with continuation
        if line.strip() == "# via" or line.strip() == "#   via":
            continue
        # Skip lines that are just continuation of via comments
        if line.strip().startswith("#   ") and any(
            pkg in line for pkg in ["deepeval", "fsspec", "langchain"]
        ):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def generate_requirements_files() -> bool:
    """Generate requirements.txt, requirements-ci.txt, and requirements-self-hosted.txt"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    requirements_in = project_root / "requirements.in"
    requirements_txt = project_root / "requirements.txt"
    requirements_ci_txt = project_root / "requirements-ci.txt"
    requirements_self_hosted_txt = project_root / "requirements-self-hosted.txt"

    if not requirements_in.exists():
        print(f"Error: {requirements_in} not found")
        return False

    print("🔧 Generating requirements files from requirements.in...")

    # Generate full requirements.txt
    print("📦 Generating requirements.txt (full dependencies)...")
    cmd = f"uv pip compile {requirements_in} -o {requirements_txt}"
    if run_command(cmd, cwd=str(project_root)) is None:
        print("❌ Failed to generate requirements.txt")
        return False
    print(f"✅ Generated {requirements_txt}")

    # Generate filtered requirements-ci.txt
    print("🏗️ Generating requirements-ci.txt (CI-optimized dependencies)...")

    # Create temporary filtered requirements.in for CI
    with tempfile.NamedTemporaryFile(mode="w", suffix=".in", delete=False) as temp_file:
        filtered_content = create_ci_requirements_in(str(requirements_in))
        temp_file.write(filtered_content)
        temp_ci_requirements_in = temp_file.name

    try:
        # Add CI-specific header
        ci_header = """# Healthcare AI CI Requirements
# Auto-generated from requirements.in with GPU/heavy ML packages excluded
# This file optimizes CI build times by excluding unnecessary dependencies
# Full dependencies available in requirements.txt for local development

"""

        cmd = f"uv pip compile {temp_ci_requirements_in} -o {requirements_ci_txt}"
        if run_command(cmd, cwd=str(project_root)) is None:
            print("❌ Failed to generate requirements-ci.txt")
            return False

        # Prepend header to CI requirements and clean up via comments
        with open(requirements_ci_txt) as f:
            ci_content = f.read()

        # Clean up the pip-compile generated content
        cleaned_content = clean_requirements_content(ci_content)

        with open(requirements_ci_txt, "w") as f:
            f.write(ci_header + cleaned_content)

        print(f"✅ Generated {requirements_ci_txt}")

    finally:
        # Clean up temp file
        os.unlink(temp_ci_requirements_in)

    # Generate filtered requirements-self-hosted.txt
    print("🚀 Generating requirements-self-hosted.txt (GPU-enabled, dev-packages excluded)...")

    # Create temporary filtered requirements.in for self-hosted
    with tempfile.NamedTemporaryFile(mode="w", suffix=".in", delete=False) as temp_file:
        filtered_content = create_self_hosted_requirements_in(str(requirements_in))
        temp_file.write(filtered_content)
        temp_self_hosted_requirements_in = temp_file.name

    try:
        # Add self-hosted-specific header
        self_hosted_header = """# Healthcare AI Self-Hosted Requirements
# Auto-generated from requirements.in with development packages excluded
# This file includes GPU/PyTorch packages for self-hosted runners
# But excludes development-only packages to optimize cache size

"""

        cmd = f"uv pip compile {temp_self_hosted_requirements_in} -o {requirements_self_hosted_txt}"
        if run_command(cmd, cwd=str(project_root)) is None:
            print("❌ Failed to generate requirements-self-hosted.txt")
            return False

        # Prepend header to self-hosted requirements and clean up via comments
        with open(requirements_self_hosted_txt) as f:
            self_hosted_content = f.read()

        # Clean up the pip-compile generated content
        cleaned_content = clean_requirements_content(self_hosted_content)

        with open(requirements_self_hosted_txt, "w") as f:
            f.write(self_hosted_header + cleaned_content)

        print(f"✅ Generated {requirements_self_hosted_txt}")

    finally:
        # Clean up temp file
        os.unlink(temp_self_hosted_requirements_in)

    # Show size comparison
    full_size = os.path.getsize(requirements_txt)
    ci_size = os.path.getsize(requirements_ci_txt)
    self_hosted_size = os.path.getsize(requirements_self_hosted_txt)

    ci_reduction = ((full_size - ci_size) / full_size) * 100
    self_hosted_reduction = ((full_size - self_hosted_size) / full_size) * 100

    print("\n📊 Size comparison:")
    print(f"   requirements.txt: {full_size:,} bytes (full)")
    print(f"   requirements-ci.txt: {ci_size:,} bytes ({ci_reduction:.1f}% reduction)")
    print(
        f"   requirements-self-hosted.txt: {self_hosted_size:,} bytes ({self_hosted_reduction:.1f}% reduction)"
    )

    return True


def main() -> None:
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
        return

    success = generate_requirements_files()
    if not success:
        sys.exit(1)

    print("\n🎯 Requirements generation complete!")
    print("   Use 'make deps' to install full dependencies for development")
    print("   CI will automatically use requirements-ci.txt for validation")


if __name__ == "__main__":
    main()
