.PHONY: \
	   auto-repair \
	   backup \
	   debug \
	   deps \
	   diagnostics \
	   dry-run \
	   e2e \
	   fix-permissions \
	   help \
	   hooks \
	   install \
	   lint \
	   lint-python \
	   reset \
	   restore \
	   setup \
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

# Constants (matching bootstrap.sh)
DEFAULT_UID := 1000
DEFAULT_GID := 1001
CFG_UID := $(or $(CFG_UID),$(DEFAULT_UID))
CFG_GID := $(or $(CFG_GID),$(DEFAULT_GID))

# Production directories to symlink (excluding development dirs: archive, coverage, docs, reference, test)
# Note: logs is excluded - it should remain as a real directory in /opt/intelluxe/logs for systemd services
PROD_DIRS := agents config core data infrastructure mcps notebooks scripts services stack systemd

# Installation Commands
install:
	@echo "🔗  Installing Intelluxe AI healthcare infrastructure scripts and services"
	@echo "   - Creating intelluxe user and group if they don't exist"
	@if ! getent group intelluxe >/dev/null; then \
	    sudo groupadd --gid $(CFG_GID) intelluxe; \
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
	@echo "   - Fixing systemd service files"
	@bash scripts/fix-systemd-units.sh
	@echo "   - Installing systemd units to /etc/systemd/system/ with intelluxe- prefix (using symlinks)"
	@for unit in $(PWD)/systemd/*.service $(PWD)/systemd/*.timer; do \
	    if [ -f "$$unit" ]; then \
	        unit_name=$$(basename "$$unit"); \
	        sudo ln -sf "$$unit" "/etc/systemd/system/intelluxe-$$unit_name"; \
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
	@echo "   - Creating /opt/intelluxe base directory"
	@sudo mkdir -p /opt/intelluxe
	@echo "   - Symlinking production directories to /opt/intelluxe/"
	@for dir in $(PROD_DIRS); do \
	    if [ -d "$(PWD)/$$dir" ]; then \
	        echo "     Symlinking $$dir -> /opt/intelluxe/$$dir"; \
	        sudo ln -sf $(PWD)/$$dir /opt/intelluxe/; \
	    fi; \
	done
	@echo "   - Setting correct permissions using CFG_UID:CFG_GID ($(CFG_UID):$(CFG_GID))"
	@sudo chmod 755 $(PWD)/scripts/*.sh $(PWD)/scripts/*.py
	@for dir in $(PROD_DIRS); do \
	    if [ -d "$(PWD)/$$dir" ]; then \
	        sudo chown -R $(CFG_UID):$(CFG_GID) $(PWD)/$$dir; \
	    fi; \
	done
	@sudo chmod -R g+w $(PWD)/stack
	@sudo find $(PWD)/stack -name "*.conf" -o -name "*.env" | xargs -r sudo chmod 660
	@sudo find $(PWD)/stack -name "*.log" | xargs -r sudo chmod 664
	@sudo chown -R $(CFG_UID):$(CFG_GID) /opt/intelluxe
	@if [ -f "/opt/intelluxe/stack/.bootstrap.conf" ]; then \
	    sudo chown $(CFG_UID):$(CFG_GID) /opt/intelluxe/stack/.bootstrap.conf; \
	fi
	@echo "✅  Healthcare AI infrastructure installation complete! Run 'make setup' to configure."

uninstall:
	@echo "🗑️  Removing Intelluxe healthcare AI systemd units and directories"
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
	@echo "🔧  Fixing permissions and ownership for healthcare AI files"
	@if ! getent group intelluxe >/dev/null; then \
	    sudo groupadd --gid $(CFG_GID) intelluxe; \
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
	@for dir in $(PROD_DIRS); do \
	    if [ -d "$$dir" ]; then \
	        sudo chown -R $(CFG_UID):$(CFG_GID) $$dir; \
	    fi; \
	done
	@echo "   - Setting development permissions on healthcare AI stack files"
	@sudo chmod -R g+w stack
	@sudo find stack -name "*.conf" -o -name "*.env" | xargs -r sudo chmod 660
	@sudo find stack -name "*.log" | xargs -r sudo chmod 664
	@sudo chown -R $(CFG_UID):$(CFG_GID) /opt/intelluxe
	@echo "   - Installing systemd units with intelluxe- prefix if missing (using symlinks)"
	@for unit in $(PWD)/systemd/*.service $(PWD)/systemd/*.timer; do \
	    if [ -f "$$unit" ]; then \
	        unit_name=$$(basename "$$unit"); \
	        if [ ! -f "/etc/systemd/system/intelluxe-$$unit_name" ]; then \
	            sudo ln -sf "$$unit" "/etc/systemd/system/intelluxe-$$unit_name"; \
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
	@echo "📦  Installing healthcare AI dependencies for development (all packages)"
	@# Generate lockfiles first if they don't exist or requirements.in is newer
	@if [ ! -f requirements.txt ] || [ requirements.in -nt requirements.txt ]; then \
		echo "🔒  Generating lockfiles from requirements.in..."; \
		python3 scripts/generate-requirements.py; \
	fi
	@# Install formatting tools for git hooks
	@echo "🎨  Installing formatting tools for pre-commit hooks..."
	@if command -v npm >/dev/null 2>&1; then \
		sudo npm install -g prettier; \
	else \
		echo "⚠️  npm not found - prettier not installed (for YAML/JSON/Markdown formatting)"; \
	fi
	@if command -v go >/dev/null 2>&1; then \
		go install mvdan.cc/sh/v3/cmd/shfmt@latest; \
	else \
		echo "⚠️  go not found - shfmt not installed (for shell script formatting)"; \
	fi
	@# Try to install dependencies using the best available method
	@if command -v uv >/dev/null 2>&1; then \
		echo "🚀  Using uv for fast installation (development = all dependencies)..."; \
		sudo uv pip install --system --break-system-packages flake8 mypy pytest pytest-asyncio yamllint; \
		if [ -f requirements.txt ]; then \
			sudo uv pip install --system --break-system-packages -r requirements.txt; \
		fi; \
	else \
		echo "⚠️  UV not found, installing with pip..."; \
		if ! command -v uv >/dev/null 2>&1; then \
			echo "🔧  Installing uv for faster Python package management..."; \
			curl -LsSf https://astral.sh/uv/install.sh | sh; \
			export PATH="$$HOME/.cargo/bin:$$PATH"; \
		fi; \
		pip3 install --user --break-system-packages flake8 mypy pytest pytest-asyncio yamllint; \
		if [ -f requirements.txt ]; then \
			pip3 install --user --break-system-packages -r requirements.txt; \
		fi; \
	fi
	@echo "✅  All development dependencies installed successfully"

update:
	@echo "🔄  Running healthcare AI system update and upgrade"
	sudo ./scripts/auto-upgrade.sh

# Update and regenerate lockfiles
update-deps:
	@echo "🔄  Updating healthcare AI dependencies"
	@if command -v uv >/dev/null 2>&1; then \
		python3 scripts/generate-requirements.py; \
		uv pip install -r requirements.txt; \
	else \
		pip install --upgrade -r requirements.in; \
	fi

# Main Setup Commands
setup:
	@echo "🚀  Setting up complete Intelluxe AI healthcare stack (interactive)"
	./scripts/bootstrap.sh

dry-run:
	@echo "🔍  Preview Intelluxe AI healthcare setup without making changes"
	./scripts/bootstrap.sh --dry-run --non-interactive

debug:
	@echo "🐛  Debug healthcare AI setup with verbose output and detailed logging"
	./scripts/bootstrap.sh --dry-run --non-interactive --debug

# Management Commands
diagnostics:
	@echo "🔍  Running comprehensive healthcare AI system diagnostics"
	./scripts/diagnostics.sh

auto-repair:
	@echo "🔧  Automatically repairing unhealthy healthcare AI containers"
	./scripts/bootstrap.sh --auto-repair

reset:
	@echo "🔄  Resetting entire healthcare AI stack (containers + config)"
	./scripts/bootstrap.sh --reset

teardown:
	@echo "🧹  Complete teardown of Intelluxe AI healthcare infrastructure"
	./scripts/teardown.sh

teardown-vpn:
	@echo "🔒  Removing VPN components only (preserving healthcare AI services)"
	./scripts/bootstrap.sh --wg-down

# Backup and Restore
backup:
	@echo "💾  Creating backup of WireGuard healthcare VPN configuration"
	./scripts/bootstrap.sh --backup

restore:
	@echo "📂  Restore healthcare AI configuration from backup (requires BACKUP_FILE variable)"
	@if [ -z "$(BACKUP_FILE)" ]; then \
	    echo "❌ Error: BACKUP_FILE variable not set"; \
	    echo "Usage: make restore BACKUP_FILE=/path/to/backup.tar.gz"; \
	    exit 1; \
	fi
	./scripts/bootstrap.sh --restore-backup "$(BACKUP_FILE)"

# Development Commands
hooks:
	@echo "🔗  Installing git hooks for pre-push validation"
	./.githooks/install-hooks.sh

lint:
	@echo "🔍  Running shellcheck with warning level for healthcare AI scripts"
	@shellcheck -S warning --format=gcc -x $$(find scripts -name "*.sh")
	$(MAKE) lint-python

lint-python:
	@echo "🔍  Running Python lint (flake8 and mypy) for healthcare AI components"
	@# Try multiple ways to find flake8 (system package, command, python module)
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 scripts/*.py test/python/*.py; \
	elif python3 -m flake8 --version >/dev/null 2>&1; then \
		python3 -m flake8 scripts/*.py test/python/*.py; \
	else \
		echo "⚠️  flake8 not found - trying to install..."; \
		if command -v apt >/dev/null 2>&1; then \
			echo "Trying system package installation..."; \
			sudo apt install -y python3-flake8 2>/dev/null || true; \
		fi; \
		if ! command -v flake8 >/dev/null 2>&1 && ! python3 -m flake8 --version >/dev/null 2>&1; then \
			python3 -m pip install --user --break-system-packages flake8 || echo "Failed to install flake8"; \
		fi; \
		if command -v flake8 >/dev/null 2>&1; then \
			flake8 scripts/*.py test/python/*.py; \
		elif python3 -m flake8 --version >/dev/null 2>&1; then \
			python3 -m flake8 scripts/*.py test/python/*.py; \
		else \
			echo "❌ flake8 still not available after installation"; \
			exit 1; \
		fi; \
	fi
	@# Try multiple ways to find mypy
	@if command -v mypy >/dev/null 2>&1; then \
		mypy scripts/*.py; \
	elif python3 -m mypy --version >/dev/null 2>&1; then \
		python3 -m mypy scripts/*.py; \
	else \
		echo "⚠️  mypy not found - trying to install..."; \
		python3 -m pip install --user --break-system-packages mypy || echo "Failed to install mypy"; \
		if command -v mypy >/dev/null 2>&1; then \
			mypy scripts/*.py; \
		elif python3 -m mypy --version >/dev/null 2>&1; then \
			python3 -m mypy scripts/*.py; \
		else \
			echo "❌ mypy still not available after installation"; \
			exit 1; \
		fi; \
	fi

validate:
	@echo "✅  Validating healthcare AI configuration and dependencies (non-interactive)"
	@if [ "${CI}" = "true" ]; then \
		if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then \
			./scripts/bootstrap.sh --validate --non-interactive --skip-docker-check; \
			$(MAKE) systemd-verify; \
		else \
			echo "Skipping Docker validation in CI: Docker not available"; \
			./scripts/bootstrap.sh --validate --non-interactive --skip-docker-check --dry-run; \
		fi; \
	else \
		./scripts/bootstrap.sh --validate --non-interactive; \
		$(MAKE) systemd-verify; \
	fi

systemd-verify:
	@echo "🔧  Verifying healthcare AI systemd service configurations"
	@./scripts/systemd-verify.sh

test:
	@echo "🧪  Running healthcare AI Bats tests"
	@if [ "${CI}" = "true" ]; then \
		echo "Running healthcare AI tests in CI mode with appropriate skips"; \
		CI=true bash ./scripts/test.sh; \
	else \
		bash ./scripts/test.sh; \
	fi

test-quiet:
	@echo "🧪  Running healthcare AI Bats tests (quiet mode)"
	QUIET=true bash ./scripts/test.sh

test-coverage:
	@echo "🧪  Running healthcare AI Bats tests with coverage (if available)"
	USE_KCOV=true bash ./scripts/test.sh

# Virtual environment management
venv:
	@echo "💡  To use virtual environment for healthcare AI development:"
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

e2e:
	@echo "🚀  Running end-to-end healthcare AI bootstrap test"
	bash test/e2e/run-bootstrap.sh

# Help
help:
	@echo "🏥  Intelluxe AI Healthcare Infrastructure Management"
	@echo "================================================="
	@echo ""
	@echo "�️  Quick Developer Setup:"
	@echo "  make install         Install system-wide (production-like paths)"
	@echo "  make deps            Install development dependencies"
	@echo "  make hooks           Install git hooks for code quality"
	@echo "  make validate        Verify setup works"
	@echo ""
	@echo "�📦 Installation:"
	@echo "  make install         Install healthcare AI scripts and systemd services system-wide"
	@echo "  make update          Run system update and upgrade"
	@echo ""
	@echo "🚀 Setup:"
	@echo "  make setup           Interactive healthcare AI setup (recommended for first run)"
	@echo "  make dry-run         Preview setup without making changes"
	@echo "  make debug           Debug dry-run with verbose output and detailed logging"
	@echo ""
	@echo "🔧 Management:"
	@echo "  make diagnostics     Run comprehensive healthcare AI system health checks"
	@echo "  make auto-repair     Automatically repair unhealthy healthcare AI containers"
	@echo "  make reset           Reset entire healthcare AI stack (containers + config)"
	@echo "  make teardown        Complete healthcare AI infrastructure teardown"
	@echo "  make teardown-vpn    Remove VPN components only (preserving healthcare AI services)"
	@echo ""
	@echo "💾 Backup/Restore:"
	@echo "  make backup          Create WireGuard healthcare VPN configuration backup"
	@echo "  make restore BACKUP_FILE=<path>  Restore from backup file"
	@echo ""
	@echo "🛠️  Development:"
	@echo "  make deps            Install healthcare AI lint and test dependencies"
	@echo "  make update-deps     Update and regenerate dependency lockfiles"
	@echo "  make venv            Create or activate a virtual environment"
	@echo "  make hooks           Install git hooks for pre-push validation"
	@echo "  make lint            Run shell and Python linters for healthcare AI code"
	@echo "  make lint-python     Run Python-specific linting (flake8, mypy)"
	@echo "  make validate        Validate healthcare AI configuration and dependencies"
	@echo "  make test            Run healthcare AI unit tests with Bats"
	@echo "  make test-quiet      Run healthcare AI tests (quiet mode)"
	@echo "  make test-coverage   Run healthcare AI tests with coverage"
	@echo "  make e2e             Run end-to-end healthcare AI bootstrap test"
	@echo "  make systemd-verify  Verify healthcare AI systemd service configurations"
	@echo ""
	@echo "🔧 Maintenance:"
	@echo "  make fix-permissions Fix ownership and permissions for healthcare AI files"
	@echo ""
	@echo "  make help            Show this help message"
