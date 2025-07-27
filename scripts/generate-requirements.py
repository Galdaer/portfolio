#!/usr/bin/env python3
"""
Generate requirements.txt and requirements-ci.txt from requirements.in

This script generates two requirements files:
- requirements.txt: Full dependencies for local development and production
- requirements-ci.txt: Minimal dependencies for CI/CD validation

Heavy GPU/ML packages are excluded from CI to improve build times and efficiency.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

# Packages that should be excluded from CI (GPU, heavy ML packages)
CI_EXCLUDED_PACKAGES = {
    # GPU/CUDA packages
    'torch',
    'nvidia-cublas-cu12',
    'nvidia-cuda-cupti-cu12',
    'nvidia-cuda-nvrtc-cu12',
    'nvidia-cuda-runtime-cu12',
    'nvidia-cudnn-cu12',
    'nvidia-cufft-cu12',
    'nvidia-cufile-cu12',
    'nvidia-curand-cu12',
    'nvidia-cusolver-cu12',
    'nvidia-cusparse-cu12',
    'nvidia-cusparselt-cu12',
    'nvidia-nccl-cu12',
    'nvidia-nvjitlink-cu12',
    'nvidia-nvtx-cu12',
    'triton',

    # Heavy ML/AI packages not needed for validation
    'unsloth',
    'unsloth-zoo',
    'accelerate',
    'bitsandbytes',
    'trl',
    'wandb',
    'datasets',
    'transformers',
    'peft',

    # Large data processing packages
    'matplotlib',
    'seaborn',
    'pandas',
    'scipy',
    'scikit-learn',
    'pillow',

    # Audio/video processing (if any)
    'ffmpeg',
    'opencv-python',

    # Development packages that aren't needed in CI
    'jupyter',
    'notebook',
    'ipython',
}

# Core packages that CI validation DOES need
CI_REQUIRED_PACKAGES = {
    # Web framework and API
    'flask',
    'fastapi',
    'uvicorn',
    'pydantic',
    'pydantic-settings',
    'starlette',

    # Database and storage
    'sqlalchemy',
    'alembic',
    'redis',
    'asyncpg',
    'psycopg2-binary',

    # HTTP clients and async
    'httpx',
    'aiofiles',
    'requests',

    # Authentication and security
    'python-multipart',
    'python-jose',
    'pyjwt',
    'passlib',
    'bcrypt',
    'cryptography',

    # Configuration
    'python-dotenv',
    'pyyaml',
    'jinja2',

    # Testing and validation
    'pytest',
    'pytest-asyncio',
    'flake8',
    'mypy',
    'yamllint',
    'black',
    'isort',
    'pylint',

    # Healthcare-specific
    'fastmcp',
    'presidio-analyzer',
    'presidio-anonymizer',
    'structlog',

    # Core AI (lightweight)
    'langchain',
    'langgraph',
    'chromadb',
    'qdrant-client',
    'faiss-cpu',

    # Monitoring
    'prometheus-client',

    # Type stubs
    'types-requests',
}

def run_command(cmd, cwd=None):
    """Run a command and return the result"""
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

def create_ci_requirements_in(requirements_in_path):
    """Create a filtered requirements.in for CI by excluding heavy packages"""
    with open(requirements_in_path, 'r') as f:
        lines = f.readlines()

    filtered_lines = []

    for line in lines:
        line_stripped = line.strip()

        # Skip comments and empty lines
        if not line_stripped or line_stripped.startswith('#'):
            filtered_lines.append(line)
            continue

        # Check if this line contains a package we want to exclude
        package_name = line_stripped.split('>=')[0].split('==')[0].split('[')[0].split('@')[0].strip()

        if package_name in CI_EXCLUDED_PACKAGES:
            print(f"Excluding from CI: {package_name}")
            continue

        filtered_lines.append(line)

    return ''.join(filtered_lines)

def generate_requirements_files():
    """Generate both requirements.txt and requirements-ci.txt"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    requirements_in = project_root / "requirements.in"
    requirements_txt = project_root / "requirements.txt"
    requirements_ci_txt = project_root / "requirements-ci.txt"

    if not requirements_in.exists():
        print(f"Error: {requirements_in} not found")
        return False

    print("🔧 Generating requirements files from requirements.in...")

    # Generate full requirements.txt
    print("📦 Generating requirements.txt (full dependencies)...")
    cmd = f"uv pip compile {requirements_in} -o {requirements_txt}"
    if run_command(cmd, cwd=project_root) is None:
        print("❌ Failed to generate requirements.txt")
        return False
    print(f"✅ Generated {requirements_txt}")

    # Generate filtered requirements-ci.txt
    print("🏗️ Generating requirements-ci.txt (CI-optimized dependencies)...")

    # Create temporary filtered requirements.in
    with tempfile.NamedTemporaryFile(mode='w', suffix='.in', delete=False) as temp_file:
        filtered_content = create_ci_requirements_in(requirements_in)
        temp_file.write(filtered_content)
        temp_requirements_in = temp_file.name

    try:
        # Add CI-specific header
        ci_header = """# Healthcare AI CI Requirements
# Auto-generated from requirements.in with GPU/heavy ML packages excluded
# This file optimizes CI build times by excluding unnecessary dependencies
# Full dependencies available in requirements.txt for local development

"""

        cmd = f"uv pip compile {temp_requirements_in} -o {requirements_ci_txt}"
        if run_command(cmd, cwd=project_root) is None:
            print("❌ Failed to generate requirements-ci.txt")
            return False

        # Prepend header to CI requirements
        with open(requirements_ci_txt, 'r') as f:
            ci_content = f.read()
        with open(requirements_ci_txt, 'w') as f:
            f.write(ci_header + ci_content)

        print(f"✅ Generated {requirements_ci_txt}")

        # Show size comparison
        full_size = os.path.getsize(requirements_txt)
        ci_size = os.path.getsize(requirements_ci_txt)
        reduction = ((full_size - ci_size) / full_size) * 100

        print("\n📊 Size comparison:")
        print(f"   requirements.txt: {full_size:,} bytes")
        print(f"   requirements-ci.txt: {ci_size:,} bytes")
        print(f"   Reduction: {reduction:.1f}%")

        return True

    finally:
        # Clean up temp file
        os.unlink(temp_requirements_in)

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
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
