.PHONY: \
	   auto-repair \
	   backup \
	   debug \
	   deps \
	   diagnostics \
	   dry-run \
	   dry-run-dev \
	   e2e \
	   fix-permissions \
	   help \
	   install \
	   lint \
	   lint-python \
	   reset \
	   restore \
	   setup \
	   setup-dev \
	   setup-open \
	   setup-restricted \
	   sync-systemd \
	   systemd-verify \
	   teardown \
	   teardown-vpn \
	   test \
	   test-coverage \
	   test-quiet \
	   uninstall \
	   update \
	   validate \
	   venv

# Installation Commands
install:
	@echo "🔗  Installing Intelluxe AI infrastructure scripts and services"
	@echo "   - Creating intelluxe user and group if they don't exist"
	@if ! getent group intelluxe >/dev/null; then \
		sudo groupadd intelluxe; \
	fi
	@if ! getent passwd intelluxe >/dev/null; then \
		sudo useradd -r -g intelluxe -s /bin/false -d /opt/intelluxe intelluxe; \
	fi
	@echo "   - Adding current user to intelluxe group"
	@sudo usermod -a -G intelluxe $(shell whoami)
	@echo "   - Verifying group membership"
	@if ! getent group intelluxe | grep -q $(shell whoami); then \
		echo "ERROR: Group membership not applied correctly"; \
		exit 1; \
	fi
	sudo mkdir -p /opt/intelluxe/scripts
	@echo "   - Fixing systemd service files"
	@bash scripts/fix-systemd-units.sh
	@echo "   - Installing systemd units to /etc/systemd/system/ with intelluxe- prefix"
	@for unit in $(PWD)/systemd/*.service $(PWD)/systemd/*.timer; do \
		if [ -f "$$unit" ]; then \
			unit_name=$$(basename "$$unit"); \
			sudo install -m 644 "$$unit" "/etc/systemd/system/intelluxe-$$unit_name"; \
		fi; \
	done
	@echo "   - Enabling systemd units"
	@for unit in $(PWD)/systemd/*.service $(PWD)/systemd/*.timer; do \
		if [ -f "$$unit" ]; then \
			unit_name=$$(basename "$$unit"); \
			sudo systemctl enable "intelluxe-$$unit_name" 2>/dev/null || echo "Note: intelluxe-$$unit_name may have dependency issues, will be resolved after daemon-reload"; \
		fi; \
	done
	sudo systemctl daemon-reload
	@echo "   - Symlinking /home/intelluxe/stack to /opt/intelluxe/stack"
	sudo ln -sf $(PWD)/stack /opt/intelluxe/
	@echo "   - Symlinking /home/intelluxe/scripts to /opt/intelluxe/scripts"
	sudo ln -sf $(PWD)/scripts /opt/intelluxe/scripts
	@echo "   - Setting correct permissions on script files"
	@sudo chmod 755 $(PWD)/scripts/*.sh $(PWD)/scripts/*.py
	@echo "   - Setting development ownership on source files (user:intelluxe)"
	@sudo chown -R $(shell whoami):intelluxe $(PWD)/scripts $(PWD)/stack
	@echo "   - Setting development permissions on stack files (group-writable)"
	@sudo chmod -R g+w $(PWD)/stack
	@sudo find $(PWD)/stack -name "*.conf" -o -name "*.env" | xargs -r sudo chmod 660
	@sudo find $(PWD)/stack -name "*.log" | xargs -r sudo chmod 664
	@echo "   - Setting correct ownership on symlinked files"
	@sudo chown -R intelluxe:intelluxe /opt/intelluxe
	@if [ -f "/opt/intelluxe/stack/.bootstrap.conf" ]; then \
		sudo chown intelluxe:intelluxe /opt/intelluxe/stack/.bootstrap.conf; \
	fi
	@echo "✅  Installation complete! Run 'make setup' to configure your Intelluxe AI system."

uninstall:
	@echo "🗑️  Removing Intelluxe systemd units and directories"
	@echo "   - Disabling and stopping Intelluxe systemd units"
	@for unit in /etc/systemd/system/intelluxe-*.service /etc/systemd/system/intelluxe-*.timer; do \
		if [ -f "$$unit" ]; then \
			unit_name=$$(basename "$$unit"); \
			sudo systemctl disable "$$unit_name" 2>/dev/null || true; \
			sudo systemctl stop "$$unit_name" 2>/dev/null || true; \
		fi; \
	done 2>/dev/null || true
	@echo "   - Removing Intelluxe systemd unit files"
	sudo rm -f /etc/systemd/system/intelluxe-*.service /etc/systemd/system/intelluxe-*.timer
	@echo "   - Removing Intelluxe directories"
	sudo rm -rf /opt/intelluxe
	sudo systemctl daemon-reload
	@echo "✅ Uninstall complete"

fix-permissions:
	@echo "🔧  Fixing permissions and ownership for Intelluxe files"
	@if ! getent group intelluxe >/dev/null; then \
		sudo groupadd intelluxe; \
	fi
	@if ! getent passwd intelluxe >/dev/null; then \
		sudo useradd -r -g intelluxe -s /bin/false -d /opt/intelluxe intelluxe; \
	fi
	@sudo usermod -a -G intelluxe $(shell whoami)
	@echo "   - Verifying group membership"
	@if ! getent group intelluxe | grep -q $(shell whoami); then \
		echo "ERROR: Group membership not applied correctly"; \
		exit 1; \
	fi
	@sudo chmod 755 scripts/*.sh scripts/*.py
	@sudo chown -R $(shell whoami):intelluxe scripts stack
	@echo "   - Setting development permissions on stack files"
	@sudo chmod -R g+w stack
	@sudo find stack -name "*.conf" -o -name "*.env" | xargs -r sudo chmod 660
	@sudo find stack -name "*.log" | xargs -r sudo chmod 664
	@sudo chown -R intelluxe:intelluxe /opt/intelluxe
	@echo "   - Installing systemd units with intelluxe- prefix if missing"
	@for unit in $(PWD)/systemd/*.service $(PWD)/systemd/*.timer; do \
		if [ -f "$$unit" ]; then \
			unit_name=$$(basename "$$unit"); \
			if [ ! -f "/etc/systemd/system/intelluxe-$$unit_name" ]; then \
				sudo install -m 644 "$$unit" "/etc/systemd/system/intelluxe-$$unit_name"; \
			fi; \
		fi; \
	done 2>/dev/null || true
	@echo "   - Enabling systemd units"
	@for unit in $(PWD)/systemd/*.service $(PWD)/systemd/*.timer; do \
		if [ -f "$$unit" ]; then \
			unit_name=$$(basename "$$unit"); \
			sudo systemctl enable "intelluxe-$$unit_name" 2>/dev/null || true; \
		fi; \
	done 2>/dev/null || true
	@bash scripts/fix-systemd-units.sh
	@sudo systemctl daemon-reload
	@echo "✅ Permissions and ownership fixed"

deps:
	@echo "📦  Installing system dependencies first"
	@if [ ! -x "./scripts/setup-environment.sh" ]; then \
		echo "❌ setup-environment.sh not found" >&2; \
		exit 1; \
	fi
	@echo "⚠️  Note: This will install system packages (Docker, UV, etc.) but not Python packages"
	@sudo SKIP_PYTHON_PACKAGES=1 ./scripts/setup-environment.sh || { \
		echo "❌ System dependency installation failed" >&2; exit 1; \
	}
	@echo "📦  Installing Python dependencies in virtual environment with UV"
	@if [ ! -f "requirements.in" ]; then \
		echo "❌ requirements.in not found" >&2; \
		exit 1; \
	fi
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "⚠️  No virtual environment detected. Creating one..."; \
		python3 -m venv .venv; \
		echo "💡 Virtual environment created. Activate it with: source .venv/bin/activate"; \
		echo "💡 Then run 'make deps' again"; \
		exit 1; \
	fi
	@if command -v uv >/dev/null 2>&1; then \
		echo "🚀 Installing with UV (fast) in virtual environment..."; \
		uv pip install -r requirements.in; \
		uv pip compile requirements.in -o requirements.lock; \
		uv pip freeze > requirements.txt; \
		echo "✅ Python dependencies installed in virtual environment"; \
	else \
		echo "⚠️  UV not found, installing with pip (slower)..."; \
		pip install -r requirements.in; \
	fi

update:
	@echo "🔄  Running system update and upgrade"
	sudo ./scripts/auto-upgrade.sh

# Main Setup Commands
setup:
	@echo "🚀  Setting up complete intelluxe stack (interactive mode)"
	./scripts/bootstrap.sh

dry-run:
	@echo "🔍  Preview intelluxe setup without making changes"
	sudo ./scripts/bootstrap.sh --dry-run --non-interactive

debug:
	@echo "🐛  Debug dry-run with verbose output and detailed logging"
	sudo ./scripts/bootstrap.sh --dry-run --non-interactive --debug

setup-restricted:
	@echo "🔒  Setting up intelluxe with all services restricted to LAN + VPN only"
	sudo ./scripts/bootstrap.sh --restrict-all-services

setup-open:
	@echo "🌐  Setting up intelluxe with all services accessible from anywhere"
	sudo ./scripts/bootstrap.sh --open-all-services

# Management Commands  
diagnostics:
	@echo "🔍  Running comprehensive system diagnostics"
	sudo ./scripts/diagnostics.sh

auto-repair:
	@echo "🔧  Running automatic repair for unhealthy containers"
	sudo ./scripts/auto-repair.sh

reset:
	@echo "♻️   Resetting intelluxe stack (removes containers and reconfigures)"
	sudo ./scripts/reset.sh

teardown:
	@echo "🧹  Complete teardown of intelluxe infrastructure"
	sudo ./scripts/teardown.sh

teardown-vpn:
	@echo "🧹  Teardown VPN components only"
	sudo ./scripts/teardown.sh --vpn-only

# Backup and Restore
backup:
	@echo "💾  Creating backup of WireGuard configuration"
	sudo ./scripts/bootstrap.sh --backup

restore:
	@echo "📂  Restore from backup (requires BACKUP_FILE variable)"
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "❌ Error: BACKUP_FILE variable not set"; \
		echo "Usage: make restore BACKUP_FILE=/path/to/backup.tar.gz"; \
		exit 1; \
	fi
	sudo ./scripts/bootstrap.sh --restore-backup "$(BACKUP_FILE)"

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
		sudo ./scripts/bootstrap.sh --validate --non-interactive --skip-docker-check; \
		$(MAKE) systemd-verify; \
		else \
		echo "Skipping Docker validation in CI: Docker not available"; \
		fi; \
		else \
		sudo ./scripts/bootstrap.sh --validate --non-interactive; \
		$(MAKE) systemd-verify; \
		fi

systemd-verify:
	@echo "🔧  Verifying systemd service configurations"
	@./scripts/systemd-verify.sh

sync-systemd: ## Sync systemd service files (development quick update)
	@echo "🔄  Syncing systemd service files..."
	@for service in systemd/*.service systemd/*.timer; do \
		if [ -f "$$service" ]; then \
			basename=$$(basename "$$service"); \
			target_name="intelluxe-$$basename"; \
			echo "Installing $$service -> /etc/systemd/system/$$target_name"; \
			sudo cp "$$service" "/etc/systemd/system/$$target_name"; \
		fi; \
	done
	@sudo systemctl daemon-reload
	@echo "✅  Systemd services synced and daemon reloaded"

test:
	@echo "🧪  Running Bats tests"
	@if [ "${CI}" = "true" ]; then \
		echo "Running tests in CI mode with appropriate skips"; \
		CI=true bash ./scripts/test.sh; \
	else \
		bash ./scripts/test.sh; \
	fi

test-quiet:
	@echo "🧪  Running Bats tests (quiet mode)"
	QUIET=true bash ./scripts/test.sh

test-coverage:
	@echo "🧪  Running Bats tests with coverage (if available)"
	USE_KCOV=true bash ./scripts/test.sh

# Virtual environment management
venv:
	@echo "💡  To use virtual environment:"
	@echo "   source .venv/bin/activate"
	@echo ""
	@echo "💡  To install dependencies:"
	@echo "   make deps"
	@if [ ! -d ".venv" ]; then \
		echo "⚠️  No virtual environment found. Creating one..."; \
		python3 -m venv .venv; \
		echo "💡 Virtual environment created. Activate it with: source .venv/bin/activate"; \
	else \
		echo "🟢 Already in virtual environment"; \
	fi

# Example usage: make venv-run CMD="pip list"
# Or: make venv-run CMD="python main.py"

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
	@echo "  make update     	  Run system update and upgrade"
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
	@echo "  make deps 		     Install lint and test dependencies"
	@echo "  make venv	      Create or activate a virtual environment"
	@echo "  make lint            Run shell and Python linters"
	@echo "  make validate        Validate configuration and dependencies"
	@echo "  make test           Run unit tests with Bats"
	@echo "  make e2e            Run end-to-end bootstrap test"
	@echo ""
	@echo "🖥️  Virtualization:"
	@echo "  virt-manager         Launch Virtual Machine Manager (KVM/QEMU GUI) for local VM testing"
	@echo ""
	@echo "  make help            Show this help message"
