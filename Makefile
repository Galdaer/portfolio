.PHONY: \
	   auto-repair \
	   backup \
	   clean-cache \
	   data-clean \
	   data-generate \
	   data-generate-large \
	   data-generate-small \
	   data-status \
	   debug \
	   deps \
	   diagnostics \
	   dry-run \
	   e2e \
	   fix	fi; \
	if [ "$$UV_AVAILABLE" = "false" ]; then \
		echo "🐍  Using pip with apt fallbacks for maximum compatibility..."; \
		echo "   📦 Installing system Python tools via apt..."; \
		sudo apt-get update -qq && sudo apt-get install -y python3-pip python3-dev python3-setuptools python3-wheel || true; \
		echo "   🔧 Installing development tools via pip..."; \
		if sudo pip3 install --break-system-packages mypy ruff pytest pytest-asyncio yamllint 2>/dev/null; then \
			echo "   ✓ Development tools installed system-wide"; \
		elif pip3 install --user mypy ruff pytest pytest-asyncio yamllint 2>/dev/null; then \
			echo "   ✓ Development tools installed to user directory"; \
		else \
			echo "   ⚠️  pip installation failed - trying apt packages"; \
			sudo apt-get install -y python3-mypy python3-pytest python3-yaml || true; \
		fi; \
		if [ -f requirements.txt ]; then \
			echo "   📋 Installing healthcare AI requirements via pip..."; \
			if sudo pip3 install --break-system-packages -r requirements.txt 2>/dev/null; then \
				echo "   ✓ Healthcare requirements installed system-wide"; \
			elif pip3 install --user -r requirements.txt 2>/dev/null; then \
				echo "   ✓ Healthcare requirements installed to user directory"; \
			else \
				echo "   ⚠️  Some requirements may have failed - check individual packages"; \
			fi; \
		fi; \
	fi
	@echo "✅  Development dependencies installation complete"
	   help \
	   hooks \
	   install \
	   lint \
	   lint-python \
	   mcp \
	   mcp-build \
	   mcp-rebuild \
	   mcp-clean \
	   reset \
	   restore \
	   setup \
	   systemd-verify \
	   teardown \
	   teardown-vpn \
	   test \
	   test-ai \
	   test-ai-report \
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
# Note: stack is excluded - configs should remain in user space (/home/intelluxe/stack)
# Note: logs is excluded - it should remain as a real directory in /opt/intelluxe/logs for systemd services
PROD_DIRS := agents config core data infrastructure mcps notebooks scripts services systemd

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
	@echo "📦  Installing healthcare AI dependencies"
	@if [ -n "$$CI" ]; then \
		echo "    🤖 CI mode detected - will use requirements-ci.txt (excludes GPU packages)"; \
	else \
		echo "    🖥️  Development mode - will use requirements.txt (all packages)"; \
	fi
	@# Generate lockfiles first if they don't exist or requirements.in is newer
	@if [ ! -f requirements.txt ] || [ requirements.in -nt requirements.txt ]; then \
		echo "🔒  Generating lockfiles from requirements.in..."; \
		python3 scripts/generate-requirements.py; \
	fi
	@# Install formatting tools for git hooks (CI-safe)
	@echo "🎨  Installing formatting tools for pre-commit hooks..."
	@if command -v npm >/dev/null 2>&1 && [ -z "$$CI" ]; then \
		sudo npm install -g prettier || echo "⚠️  npm prettier failed - continuing without it"; \
	else \
		echo "⚠️  npm not available or CI environment - skipping prettier (YAML/JSON/Markdown formatting)"; \
	fi
	@if command -v go >/dev/null 2>&1 && [ -z "$$CI" ]; then \
		go install mvdan.cc/sh/v3/cmd/shfmt@latest || echo "⚠️  go shfmt failed - continuing without it"; \
	else \
		echo "⚠️  go not available or CI environment - skipping shfmt (shell script formatting)"; \
	fi
	@# Smart dependency installation with comprehensive fallbacks
	@echo "🔍  Determining best installation method..."
	@UV_AVAILABLE=false; \
	if command -v uv >/dev/null 2>&1; then \
		echo "   ✓ uv command found"; \
		if timeout 5 uv --version >/dev/null 2>&1; then \
			echo "   ✓ uv responsive"; \
			UV_AVAILABLE=true; \
		else \
			echo "   ⚠️  uv timeout (likely firewall block)"; \
		fi; \
	else \
		echo "   ✗ uv not installed"; \
	fi; \
	if [ "$$UV_AVAILABLE" = "true" ]; then \
		echo "🚀  Using uv for ultra-fast installation..."; \
		if [ "$$CI" = "1" ]; then \
			echo "   🤖 CI mode - using user installation (no sudo required)"; \
			if timeout 30 uv pip install --user ruff pyright pytest pytest-asyncio yamllint 2>/dev/null; then \
				echo "   ✓ Core development tools installed via uv (user mode)"; \
			else \
				echo "   ⚠️  uv user installation failed - falling back to pip"; \
				UV_AVAILABLE=false; \
			fi; \
		else \
			if timeout 30 sudo uv pip install --system --break-system-packages ruff pyright pytest pytest-asyncio yamllint 2>/dev/null; then \
				echo "   ✓ Core development tools installed via uv (system mode)"; \
			else \
				echo "   ⚠️  uv system installation failed - falling back to pip"; \
				UV_AVAILABLE=false; \
			fi; \
		fi; \
		if [ "$$UV_AVAILABLE" = "true" ]; then \
			if [ -n "$$CI" ] && [ -f requirements-ci.txt ]; then \
				echo "   🤖 CI mode detected - using requirements-ci.txt (excludes GPU packages)"; \
				REQUIREMENTS_FILE=requirements-ci.txt; \
			elif [ -f requirements.txt ]; then \
				echo "   🖥️  Development mode - using requirements.txt (all packages)"; \
				REQUIREMENTS_FILE=requirements.txt; \
			else \
				echo "   ⚠️  No requirements file found"; \
				REQUIREMENTS_FILE=""; \
			fi; \
			if [ -n "$$REQUIREMENTS_FILE" ]; then \
				if [ "$$CI" = "1" ]; then \
					echo "   🤖 CI mode - using user installation (no sudo required)"; \
					if timeout 60 uv pip install --user -r "$$REQUIREMENTS_FILE" 2>/dev/null; then \
						echo "   ✓ Healthcare AI requirements installed via uv (user mode)"; \
					else \
						echo "   ⚠️  uv user installation failed - falling back to pip"; \
						UV_AVAILABLE=false; \
					fi; \
				else \
					if timeout 60 sudo uv pip install --system --break-system-packages -r "$$REQUIREMENTS_FILE" 2>/dev/null; then \
						echo "   ✓ Healthcare AI requirements installed via uv (system mode)"; \
					else \
						echo "   ⚠️  uv system installation failed - falling back to pip"; \
						UV_AVAILABLE=false; \
					fi; \
				fi; \
			fi; \
		fi; \
	else \
		echo "⚠️  UV not found or blocked, using pip and apt for CI compatibility..."; \
		echo "🐍  Installing core Python tools via apt..."; \
		sudo apt-get update -qq && sudo apt-get install -y python3-pip python3-dev python3-setuptools; \
		echo "🔧  Installing development tools via pip..."; \
		sudo pip3 install --break-system-packages mypy ruff pytest pytest-asyncio yamllint || \
		pip3 install --user mypy ruff pytest pytest-asyncio yamllint; \
		if [ -n "$$CI" ] && [ -f requirements-ci.txt ]; then \
			echo "📋  Installing CI requirements (excludes GPU packages) via pip..."; \
			sudo pip3 install --break-system-packages -r requirements-ci.txt || \
			pip3 install --user -r requirements-ci.txt; \
		elif [ -f requirements.txt ]; then \
			echo "📋  Installing full requirements via pip..."; \
			sudo pip3 install --break-system-packages -r requirements.txt || \
			pip3 install --user -r requirements.txt; \
		fi; \
	fi
	@echo "✅  All development dependencies installed successfully"

clean-cache:
	@echo "🧹  Cleaning package manager caches to free disk space"
	@# Clean uv cache
	@if command -v uv >/dev/null 2>&1; then \
		echo "   🚀 Cleaning uv cache..."; \
		uv cache clean || echo "   ⚠️  uv cache clean failed"; \
		if command -v du >/dev/null 2>&1 && uv cache dir >/dev/null 2>&1; then \
			cache_size=$$(du -sh $$(uv cache dir) 2>/dev/null | cut -f1 || echo "unknown"); \
			echo "   📊 Remaining uv cache size: $$cache_size"; \
		fi; \
	else \
		echo "   ⚠️  uv not found - skipping uv cache cleanup"; \
	fi
	@# Clean pip cache
	@if command -v pip3 >/dev/null 2>&1; then \
		echo "   🐍 Cleaning pip cache..."; \
		pip3 cache purge 2>/dev/null || echo "   ⚠️  pip cache purge failed"; \
		if command -v pip3 >/dev/null 2>&1; then \
			pip3 cache info 2>/dev/null || echo "   📊 pip cache info not available"; \
		fi; \
	else \
		echo "   ⚠️  pip3 not found - skipping pip cache cleanup"; \
	fi
	@echo "✅  Package manager cache cleanup complete"

update:
	@echo "🔄  Running healthcare AI system update and upgrade"
	sudo ./scripts/auto-upgrade.sh

# Update and regenerate lockfiles
update-deps:
	@echo "🔄  Updating healthcare AI dependencies"
	@if command -v uv >/dev/null 2>&1 && timeout 5 uv --version >/dev/null 2>&1; then \
		echo "🚀  Using uv for fast dependency updates..."; \
		python3 scripts/generate-requirements.py; \
		sudo uv pip install --system --break-system-packages -r requirements.txt; \
	else \
		echo "🐍  Using pip for dependency updates..."; \
		if [ ! -f requirements.txt ]; then \
			python3 scripts/generate-requirements.py; \
		fi; \
		sudo pip3 install --break-system-packages --upgrade -r requirements.txt || \
		pip3 install --user --upgrade -r requirements.txt; \
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

# MCP Server Build Commands
mcp: mcp-build
	@echo "✅ Healthcare MCP server build complete"

mcp-build:
	@echo "🏗️  Building Healthcare MCP server Docker image"
	@cd mcps/healthcare && docker build -t intelluxe/healthcare-mcp:latest .
	@echo "✅ Healthcare MCP Docker image built successfully"

mcp-rebuild:
	@echo "🔄  Rebuilding Healthcare MCP server (no cache)"
	@cd mcps/healthcare && docker build --no-cache -t intelluxe/healthcare-mcp:latest .
	@echo "✅ Healthcare MCP Docker image rebuilt successfully"

mcp-clean:
	@echo "🧹  Cleaning up Healthcare MCP Docker artifacts"
	@docker images intelluxe/healthcare-mcp -q | xargs -r docker rmi -f
	@docker system prune -f --filter "label=maintainer=Intelluxe AI Healthcare Team"
	@echo "✅ Healthcare MCP Docker cleanup complete"

# Development Commands
hooks:
	@echo "🔗  Installing git hooks for pre-push validation"
	./.githooks/install-hooks.sh

lint:
	@echo "🔍  Running shellcheck with warning level for healthcare AI scripts"
	@shellcheck -S warning --format=gcc -x $$(find scripts -name "*.sh")
	@echo "🔍  Checking shell function complexity patterns"
	@$(MAKE) lint-shell-complexity
	$(MAKE) lint-python

lint-shell-complexity:
	@echo "🔍  Analyzing shell functions for single responsibility violations..."
	@# Find functions >20 lines or with complex patterns
	@for script in $$(find scripts -name "*.sh"); do \
		echo "Checking $$script for function complexity..."; \
		awk '/^[a-zA-Z_][a-zA-Z0-9_]*\(\)/ { \
			func_name = $$1; gsub(/\(\)/, "", func_name); \
			func_start = NR; line_count = 0; in_function = 1; \
		} \
		in_function && /^}$$/ { \
			if (line_count > 20) \
				printf "%s:%d: Function \"%s\" has %d lines (>20) - consider refactoring for single responsibility\n", FILENAME, func_start, func_name, line_count; \
			in_function = 0; \
		} \
		in_function { line_count++ }' "$$script"; \
	done

lint-python:
	@echo "🔍  Running Python lint (ruff and mypy) for healthcare AI components"
	@# Run Ruff for linting (pyproject.toml has exclusions for submodules)
	@if command -v ruff >/dev/null 2>&1; then \
		echo "🧹 Running Ruff linting..."; \
		ruff check .; \
	elif python3 -m ruff --version >/dev/null 2>&1; then \
		echo "🧹 Running Ruff linting..."; \
		python3 -m ruff check .; \
	else \
		echo "⚠️  ruff not found - installing via make deps"; \
		$(MAKE) deps; \
		python3 -m ruff check .; \
	fi
	@# Run Ruff formatting check
	@if command -v ruff >/dev/null 2>&1; then \
		echo "🎨 Running Ruff formatting check..."; \
		ruff format --check .; \
	elif python3 -m ruff --version >/dev/null 2>&1; then \
		echo "🎨 Running Ruff formatting check..."; \
		python3 -m ruff format --check .; \
	else \
		python3 -m ruff format --check .; \
	fi
	@# Run Mypy for type checking (mypy.ini has healthcare-specific configuration)
	@if command -v dmypy >/dev/null 2>&1; then \
		echo "🚀 Running Mypy daemon for fast type checking..."; \
		dmypy run -- . || (echo "⚠️  Daemon failed, falling back to regular mypy"; mypy .); \
	elif command -v mypy >/dev/null 2>&1; then \
		echo "🔍 Running Mypy type checking..."; \
		mypy .; \
	elif python3 -m mypy --version >/dev/null 2>&1; then \
		echo "🔍 Running Mypy type checking..."; \
		python3 -m mypy .; \
	else \
		echo "⚠️  mypy not found - installing via make deps"; \
		$(MAKE) deps; \
		python3 -m mypy .; \
	fi

# Fast development linting - only core healthcare modules
lint-dev:
	@echo "🚀  Running fast development lint (core modules only)"
	@# Run Ruff for linting
	@if command -v ruff >/dev/null 2>&1; then \
		echo "🧹 Running Ruff linting..."; \
		ruff check core/ agents/ src/; \
	else \
		python3 -m ruff check core/ agents/ src/; \
	fi
	@# Run Mypy on core modules only
	@if command -v mypy >/dev/null 2>&1; then \
		echo "🔍 Running Mypy type checking (core modules)..."; \
		mypy core/ agents/ src/; \
	else \
		python3 -m mypy core/ agents/ src/; \
	fi

format:
	@echo "🎨  Running Ruff formatting on healthcare AI codebase"
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format .; \
	elif python3 -m ruff --version >/dev/null 2>&1; then \
		python3 -m ruff format .; \
	else \
		echo "⚠️  ruff not found - installing via make deps"; \
		$(MAKE) deps; \
		python3 -m ruff format .; \
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

# Synthetic Healthcare Data Generation
data-generate:
	@echo "🏥  Generating comprehensive synthetic healthcare data"
	@echo "   - 75 doctors, 2,500 patients, 6,000 encounters"
	@echo "   - Cross-referenced Phase 1 & Phase 2 business data"
	@python3 scripts/generate_synthetic_healthcare_data.py --doctors 75 --patients 2500 --encounters 6000

data-generate-small:
	@echo "🏥  Generating small test dataset"
	@echo "   - 10 doctors, 100 patients, 200 encounters"
	@python3 scripts/generate_synthetic_healthcare_data.py --doctors 10 --patients 100 --encounters 200

data-generate-large:
	@echo "🏥  Generating large development dataset"
	@echo "   - 150 doctors, 5,000 patients, 12,000 encounters"
	@python3 scripts/generate_synthetic_healthcare_data.py --doctors 150 --patients 5000 --encounters 12000

data-clean:
	@echo "🗑️  Cleaning synthetic healthcare data"
	@rm -rf data/synthetic/*.json
	@echo "✅ Synthetic data files removed"

data-status:
	@echo "📊  Synthetic Healthcare Data Status"
	@echo "=================================="
	@if [ -d "data/synthetic" ]; then \
		file_count=$$(find data/synthetic -name "*.json" -type f | wc -l); \
		if [ $$file_count -gt 0 ]; then \
			echo "📁 Files: $$file_count"; \
			total_size=$$(du -sh data/synthetic 2>/dev/null | cut -f1 || echo "unknown"); \
			echo "💾 Size: $$total_size"; \
			echo "📋 Data files:"; \
			for file in data/synthetic/*.json; do \
				if [ -f "$$file" ]; then \
					filename=$$(basename "$$file"); \
					records=$$(python3 -c "import json; print(len(json.load(open('$$file'))))" 2>/dev/null || echo "?"); \
					printf "   %-25s %s records\n" "$$filename:" "$$records"; \
				fi; \
			done; \
		else \
			echo "📂 Directory exists but no data files found"; \
		fi; \
	else \
		echo "📂 No synthetic data directory found"; \
	fi

test-ai:
	@echo "🧪  Running healthcare AI evaluation with DeepEval"
	@echo "   - Testing AI agent responses for medical accuracy"
	@echo "   - Validating HIPAA compliance and PHI protection"
	@echo "   - Measuring response quality and faithfulness"
	@echo "   - Testing Phase 1 infrastructure integration"
	@python3 tests/healthcare_evaluation/test_phase1_infrastructure.py
	@python3 scripts/healthcare_deepeval.py

test-ai-report:
	@echo "📋  Generating healthcare AI evaluation report"
	@python3 tests/healthcare_evaluation/test_phase1_infrastructure.py
	@python3 scripts/healthcare_deepeval.py
	@if [ -f "data/synthetic/healthcare_ai_evaluation_report.txt" ]; then \
		echo "📄 Report generated:"; \
		echo "   data/synthetic/healthcare_ai_evaluation_report.txt"; \
		echo "   data/synthetic/healthcare_ai_test_results.json"; \
	fi

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
	@echo "🏗️  MCP Server Build:"
	@echo "  make mcp             Build Healthcare MCP server Docker image"
	@echo "  make mcp-build       Build Healthcare MCP server Docker image"
	@echo "  make mcp-rebuild     Rebuild Healthcare MCP server (no cache)"
	@echo "  make mcp-clean       Clean up Healthcare MCP Docker artifacts"
	@echo ""
	@echo "🛠️  Development:"
	@echo "  make deps            Install healthcare AI lint and test dependencies"
	@echo "  make update-deps     Update and regenerate dependency lockfiles"
	@echo "  make clean-cache     Clean uv and pip caches to free disk space"
	@echo "  make venv            Create or activate a virtual environment"
	@echo "  make hooks           Install git hooks for pre-push validation"
	@echo "  make lint            Run shell and Python linters for healthcare AI code"
	@echo "  make lint-python     Run Python-specific linting (ruff, pyright)"
	@echo "  make format          Auto-format Python code with ruff"
	@echo "  make validate        Validate healthcare AI configuration and dependencies"
	@echo "  make test            Run healthcare AI unit tests with Bats"
	@echo "  make test-quiet      Run healthcare AI tests (quiet mode)"
	@echo "  make test-coverage   Run healthcare AI tests with coverage"
	@echo "  make test-ai         Run healthcare AI evaluation with DeepEval"
	@echo "  make test-ai-report  Generate healthcare AI evaluation report"
	@echo "  make e2e             Run end-to-end healthcare AI bootstrap test"
	@echo "  make systemd-verify  Verify healthcare AI systemd service configurations"
	@echo "  make data-small      Generate small synthetic healthcare dataset (testing)"
	@echo "  make data-dev        Generate medium synthetic healthcare dataset (development)"
	@echo "  make data-full       Generate comprehensive synthetic healthcare dataset (production-like)"
	@echo "  make data-clean      Remove all synthetic healthcare data"
	@echo ""
	@echo "🔧 Maintenance:"
	@echo "  make fix-permissions Fix ownership and permissions for healthcare AI files"
	@echo ""
	@echo "  make help            Show this help message"
