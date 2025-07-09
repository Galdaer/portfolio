.PHONY: \
       auto-repair \
       backup \
       debug \
       deps \
       diagnostics \
       dry-run \
       help \
       install \
       lint \
       reset \
       restore \
       setup \
       teardown \
       test

# Installation Commands
install:
	@echo "🔗  Installing Intelluxe AI infrastructure scripts and services"
	@echo "   - Symlinking scripts to /opt/intelluxe/scripts"
	sudo mkdir -p /opt/intelluxe/scripts
	sudo ln -sf $(PWD)/scripts/* /opt/intelluxe/scripts
	@echo "   - Installing systemd service units"
	sudo ln -sf $(PWD)/systemd/* /etc/systemd/system/
	sudo systemctl daemon-reload
	@echo "✅  Installation complete! Run 'make setup' to configure your Intelluxe AI system."

deps:
	@echo "📦  Installing lint and test dependencies"
	@if [ ! -x "./scripts/setup-environment.sh" ]; then \
		echo "❌ setup-environment.sh not found" >&2; \
		exit 1; \
	fi
	@sudo ./scripts/setup-environment.sh || { \
		echo "❌ Dependency installation failed" >&2; exit 1; \
	}

# Main Setup Commands
setup:
	@echo "🚀  Setting up complete intelluxe stack (interactive mode)"
	sudo ./scripts/clinic-bootstrap.sh

dry-run:
	@echo "🔍  Preview intelluxe setup without making changes"
	sudo ./scripts/clinic-bootstrap.sh --dry-run --non-interactive

debug:
	@echo "🐛  Debug dry-run with verbose output and detailed logging"
	sudo ./scripts/clinic-bootstrap.sh --dry-run --non-interactive --debug

setup-restricted:
	@echo "🔒  Setting up intelluxe with all services restricted to LAN + VPN only"
	sudo ./scripts/clinic-bootstrap.sh --restrict-all-services

setup-open:
	@echo "🌐  Setting up intelluxe with all services accessible from anywhere"
	sudo ./scripts/clinic-bootstrap.sh --open-all-services

# Management Commands  
diagnostics:
	@echo "🔍  Running comprehensive system diagnostics"
	sudo ./scripts/clinic-diagnostics.sh

auto-repair:
	@echo "🔧  Running automatic repair for unhealthy containers"
	sudo ./scripts/clinic-auto-repair.sh

reset:
	@echo "♻️   Resetting intelluxe stack (removes containers and reconfigures)"
	sudo ./scripts/clinic-reset.sh

teardown:
	@echo "🧹  Complete teardown of intelluxe infrastructure"
	sudo ./scripts/clinic-teardown.sh

teardown-vpn:
	@echo "🧹  Teardown VPN components only"
	sudo ./scripts/clinic-teardown.sh --vpn-only

# Backup and Restore
backup:
	@echo "💾  Creating backup of WireGuard configuration"
	sudo ./scripts/clinic-bootstrap.sh --backup

restore:
	@echo "📂  Restore from backup (requires BACKUP_FILE variable)"
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "❌ Error: BACKUP_FILE variable not set"; \
		echo "Usage: make restore BACKUP_FILE=/path/to/backup.tar.gz"; \
		exit 1; \
	fi
	sudo ./scripts/clinic-bootstrap.sh --restore-backup "$(BACKUP_FILE)"

# Development Commands
lint:
	@echo "🔍  Running shellcheck with full output"
	# Rationale: Shellcheck is used to ensure the quality and correctness of shell scripts.
	# This helps catch common issues and enforces best practices in shell scripting.
	@shellcheck -S warning --format=gcc -x $$(find scripts -name "*.sh")
	@shellcheck -S info --format=gcc -x $$(find scripts -name "*.sh")
	# Trigger Python linting after shell linting to ensure Python code quality.
	# Both linters are run to maintain high standards across different types of code.
	$(MAKE) lint-python

lint-python:
	@echo "🔍  Running Python lint (flake8 and mypy)"
	# Rationale: Flake8 checks for style issues and potential bugs in Python code.
	# Mypy performs static type checking to ensure type correctness.
	# As the project grows, consider adding new directories to linting coverage.
	# Example: Add 'src/python/*.py' or other relevant paths.
	@flake8 scripts/*.py test/python/*.py
	@mypy scripts/*.py

validate:
	@echo "✅  Validating configuration and dependencies (non-interactive)"
	@if [ "${CI}" = "true" ]; then \
	if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then \
        sudo ./scripts/clinic-bootstrap.sh --validate --non-interactive --skip-docker-check; \
        $(MAKE) systemd-verify; \
        else \
        echo "Skipping Docker validation in CI: Docker not available"; \
        fi; \
        else \
        sudo ./scripts/clinic-bootstrap.sh --validate --non-interactive; \
        $(MAKE) systemd-verify; \
        fi

test:
	@echo "🧪  Running Bats tests"
	bash ./scripts/test.sh

test-quiet:
	@echo "🧪  Running Bats tests (quiet mode)"
	QUIET=true bash ./scripts/test.sh

test-coverage:
	@echo "🧪  Running Bats tests with coverage (if available)"
	USE_KCOV=true bash ./scripts/test.sh

e2e:
	@echo "🚀  Running end-to-end bootstrap test"
	bash test/e2e/run-bootstrap.sh

# Help
help:
	@echo "�  Intelluxe AI Healthcare Infrastructure Management"
	@echo "===================================="
	@echo ""
	@echo "📦 Installation:"
	@echo "  make install         Install scripts and systemd services system-wide"
	@echo ""
	@echo "🚀 Setup:"
	@echo "  make setup           Interactive intelluxe setup (recommended for first run)"
	@echo "  make dry-run         Preview setup without making changes"
	@echo "  make debug           Debug dry-run with verbose output and detailed logging"
	@echo "  make setup-restricted Configure with LAN + VPN access only (secure)"
	@echo "  make setup-open      Configure with public access (less secure)"
	@echo ""
	@echo "🔧 Management:"
	@echo "  make diagnostics     Run comprehensive system health checks"
	@echo "  make auto-repair     Automatically repair unhealthy containers"
	@echo "  make reset           Reset entire stack (containers + config)"
	@echo "  make teardown        Complete infrastructure teardown"
	@echo "  make teardown-vpn    Remove VPN components only"
	@echo ""
	@echo "💾 Backup/Restore:"
	@echo "  make backup          Create WireGuard configuration backup"
	@echo "  make restore BACKUP_FILE=<path>  Restore from backup file"
	@echo ""
	@echo "🛠️  Development:"
	@echo "  make deps           Install lint and test dependencies"
	@echo "  make lint            Run shell and Python linters"
	@echo "  make validate        Validate configuration and dependencies"
	@echo "  make test           Run unit tests with Bats"
	@echo "  make e2e            Run end-to-end bootstrap test"
	@echo "  make help            Show this help message"
