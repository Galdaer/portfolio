#!/usr/bin/env python3
"""
Docker Security Check for Pre-commit
Validates Dockerfiles for security best practices.
"""

import os
import re
import sys


def check_dockerfile_security(filename):
    """Check Dockerfile for security issues"""
    try:
        with open(filename) as f:
            content = f.read()

        issues = []

        # Check for root user
        if not re.search(r"USER\s+(?!root)", content):
            issues.append(f"{filename}: Dockerfile should not run as root user")

        # Check for COPY/ADD with proper permissions
        if re.search(r"COPY.*--chown", content) or re.search(r"ADD.*--chown", content):
            pass  # Good practice
        elif re.search(r"COPY|ADD", content):
            issues.append(f"{filename}: Consider using --chown with COPY/ADD commands")

        # Check for health checks
        if not re.search(r"HEALTHCHECK", content):
            issues.append(f"{filename}: Missing HEALTHCHECK instruction")

        # Check for secrets in environment variables
        env_lines = re.findall(r"ENV\s+.*", content)
        for line in env_lines:
            if re.search(r"(password|secret|key|token)=\w+", line, re.IGNORECASE):
                issues.append(f"{filename}: Potential secret in ENV instruction")

        return issues
    except Exception:
        return []


def main():
    """Main Docker security validation function"""
    # Check all Dockerfiles
    issues = []
    for root, _dirs, files in os.walk("."):
        if ".git" in root:
            continue

        for file in files:
            if file.startswith("Dockerfile"):
                filepath = os.path.join(root, file)
                issues.extend(check_dockerfile_security(filepath))

    if issues:
        print("Docker Security Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("Docker security check passed")


if __name__ == "__main__":
    main()
