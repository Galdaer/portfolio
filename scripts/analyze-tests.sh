#!/usr/bin/env bash
# Script to analyze and fix failing tests

# Tests that should be skipped in CI due to environment constraints
CI_SKIP_TESTS=(
    "set_ownership uses default CFG_UID/GID"
    "set_ownership uses custom CFG_UID/GID"
    "check_docker_socket uses DOCKER_SOCKET override"
    "check_secret_perms validates secure file permissions"
    "check_docker_socket validates socket permissions"
    "rotate_log_if_needed rotates large log files"
    "build_dependency_list includes distro specific packages"
    "install_python_deps uses uv for package installation"
    "install_python_deps installs healthcare AI packages"
    "Health check succeeds when all tools exist"
    "CLI --health-check exits successfully"
    "creates log directory under CFG_ROOT"
    "overriding CFG_ROOT uses new log path"
    "LOG_DIR uses built-in CFG_ROOT"
    "invokes systemd-analyze when present"
    "exports JSON with --export-json"
    "--skip-docker-check works for validate command"
)

# Tests that have real bugs and should be fixed
REAL_BUGS=(
    "service image override respected"
    "service image override respected for traefik"
    "unknown argument prints usage and exits 1"
    "get_service_config_value handles missing files and keys"
    "get_service_config_value handles comments and whitespace"
    "build_docker_command should generate correct Docker command"
    "parse_service_config should handle missing config file"
    "build_docker_command should handle minimal configuration"
    "universal system should handle any Docker option via mapping"
    "universal system should handle unknown config options gracefully"
    "--help prints usage and exits 0"
)

echo "=== Test Analysis ==="
echo "Tests that should be skipped in CI: ${#CI_SKIP_TESTS[@]}"
echo "Tests that have real bugs: ${#REAL_BUGS[@]}"

echo ""
echo "=== CI Skip Tests ==="
for test in "${CI_SKIP_TESTS[@]}"; do
    echo "- $test"
done

echo ""
echo "=== Real Bug Tests ==="
for test in "${REAL_BUGS[@]}"; do
    echo "- $test"
done
