#!/usr/bin/env python3
"""
Generate requirements.txt and requirements-ci.txt from requirements.in

This script generates two requirements files:
- requirements.txt: Full dependencies for local development and production
- requirements-ci.txt: Minimal dependencies for CI/CD validation (cloud runners)

Heavy GPU/ML packages are excluded from CI to improve build times and efficiency.
Coding agents use requirements-ci.txt since they don't have GPU access.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Packages that should be excluded from CI (GPU, heavy ML packages)
# These are excluded because coding agents and CI runners don't have GPU access
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
    # Large data processing packages that can be loaded on-demand
    "matplotlib",
    "seaborn",
    "pandas",
    "scipy",
    "scikit-learn",
    "pillow",
    # Audio/video processing (if any)
    "ffmpeg",
    "opencv-python",
    # Development packages that aren't needed in CI/coding agents
    "jupyter",
    "notebook",
    "ipython",
}

# Core packages that CI validation DOES need (coding agents also use this list)
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
    "openai",
    # Monitoring
    "prometheus-client",
    # Type stubs
    "types-requests",
}


def run_command(cmd: str, cwd: str | None = None, timeout: int = 300) -> str | None:
    """Run a command and return the result stdout as string, or None on failure"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout
        )
        if result.returncode != 0:
            print(f"Error running command: {cmd}")
            print(f"stderr: {result.stderr}")
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"Command timed out after {timeout}s: {cmd}")
        return None
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
    """Generate requirements.txt and requirements-ci.txt"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    requirements_in = project_root / "requirements.in"
    requirements_txt = project_root / "requirements.txt"
    requirements_ci_txt = project_root / "requirements-ci.txt"

    if not requirements_in.exists():
        print(f"Error: {requirements_in} not found")
        return False

    print("🔧 Generating requirements files from requirements.in...")

    # Try uv first, fall back to pip-tools
    use_uv = run_command("uv --version") is not None
    compile_cmd = "uv pip compile" if use_uv else "pip-compile"

    if not use_uv:
        # Check if pip-tools is available
        if run_command("pip-compile --version") is None:
            print("❌ Neither uv nor pip-tools found. Installing pip-tools...")
            install_result = run_command("pip install pip-tools")
            if install_result is None:
                print("❌ Failed to install pip-tools")
                return False

    # Generate full requirements.txt
    print("📦 Generating requirements.txt (full dependencies)...")
    cmd = f"{compile_cmd} {requirements_in} -o {requirements_txt}"
    if run_command(cmd, cwd=str(project_root)) is None:
        print("❌ Failed to generate requirements.txt")
        return False
    print(f"✅ Generated {requirements_txt}")

    # Generate filtered requirements-ci.txt
    print("🏗️ Generating requirements-ci.txt (CI-optimized, also used by coding agents)...")

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

        cmd = f"{compile_cmd} {temp_ci_requirements_in} -o {requirements_ci_txt}"
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

    # Show size comparison
    full_size = os.path.getsize(requirements_txt)
    ci_size = os.path.getsize(requirements_ci_txt)

    ci_reduction = ((full_size - ci_size) / full_size) * 100

    print("\n📊 Size comparison:")
    print(f"   requirements.txt: {full_size:,} bytes (full)")
    print(f"   requirements-ci.txt: {ci_size:,} bytes ({ci_reduction:.1f}% reduction)")

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
