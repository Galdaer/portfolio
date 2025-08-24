#!/usr/bin/env python3
"""
Simple test runner for Healthcare LangChain Agent

Usage:
    python3 test_healthcare_agent.py           # Run all tests
    python3 test_healthcare_agent.py --quick   # Run quick test
    python3 test_healthcare_agent.py --docker  # Run tests inside container
"""

import subprocess
import sys


def run_tests_in_container():
    """Run tests inside the healthcare-api container"""
    print("🐳 Running tests inside healthcare-api container...")

    cmd = [
        "docker",
        "exec",
        "-it",
        "healthcare-api",
        "python3",
        "/app/tests/test_langchain_agent.py",
    ]

    try:
        subprocess.run(cmd, check=True)
        print("✅ Container tests completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Container tests failed with exit code {e.returncode}")
    except FileNotFoundError:
        print("❌ Docker not found. Make sure Docker is installed and running.")


def run_tests_locally():
    """Run tests locally"""
    print("🏠 Running tests locally...")

    # Add healthcare-api to Python path
    healthcare_api_path = "/home/intelluxe/services/user/healthcare-api"
    if healthcare_api_path not in sys.path:
        sys.path.insert(0, healthcare_api_path)

    # Import and run tests
    try:
        import asyncio

        from tests.test_langchain_agent import run_all_tests, run_quick_test

        # Check if we should run quick test
        if "--quick" in sys.argv:
            run_quick_test()
        else:
            asyncio.run(run_all_tests())

    except ImportError as e:
        print(f"❌ Failed to import test modules: {e}")
        print("💡 Try running with --docker to test inside container")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")


def main():
    """Main test runner"""
    print("🏥 Healthcare LangChain Agent Test Runner")
    print("=" * 45)

    if "--docker" in sys.argv:
        run_tests_in_container()
    else:
        run_tests_locally()


if __name__ == "__main__":
    main()
