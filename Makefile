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
	   fix-permissions \
	   format \
	   help \
	   hooks \
	   install \
	   lint \
	   lint-dev \
	   lint-python \
	   lint-shell-complexity \
	   mcp \
	   mcp-build \
	   mcp-rebuild \
	   mcp-clean \
	   medical-mirrors-build \
	   medical-mirrors-rebuild \
	   medical-mirrors-clean \
	   medical-mirrors-run \
	   medical-mirrors-logs \
	   medical-mirrors-stop \
	   medical-mirrors-health \
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
	   update-deps \
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
	        sudo systemctl enable "intelluxe-$$unit_name"; \
	    fi; \
	done
	sudo systemctl daemon-reload
	@echo "   - Creating /opt/intelluxe base directory"
	@sudo mkdir -p /opt/intelluxe
	@echo "   - Symlinking production directories to /opt/intelluxe/"
	@for dir in $(PROD_DIRS); do \
	    if [ -d "$(PWD)/$$dir" ]; then \
	        sudo ln -sf "$(PWD)/$$dir" "/opt/intelluxe/$$dir"; \
	    fi; \
	done
	@echo "   - Setting correct permissions using CFG_UID:CFG_GID ($(CFG_UID):$(CFG_GID))"
	@sudo chmod 755 $(PWD)/scripts/*.sh $(PWD)/scripts/*.py
	@for dir in $(PROD_DIRS); do \
	    if [ -d "$(PWD)/$$dir" ]; then \
	        sudo chown -R $(CFG_UID):$(CFG_GID) "$(PWD)/$$dir"; \
	        sudo chmod -R 755 "$(PWD)/$$dir"; \
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
	        sudo systemctl disable "$$(basename $$unit)" 2>/dev/null || true; \
	        sudo systemctl stop "$$(basename $$unit)" 2>/dev/null || true; \
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
	    if [ -d "$(PWD)/$$dir" ]; then \
	        sudo chown -R $(CFG_UID):$(CFG_GID) "$(PWD)/$$dir"; \
	        sudo chmod -R 755 "$(PWD)/$$dir"; \
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
	        sudo ln -sf "$$unit" "/etc/systemd/system/intelluxe-$$unit_name"; \
	    fi; \
	done 2>/dev/null || true
	@echo "   - Enabling systemd units"
	@for unit in $(PWD)/systemd/*.service $(PWD)/systemd/*.timer; do \
	    if [ -f "$$unit" ]; then \
	        unit_name=$$(basename "$$unit"); \
	        sudo systemctl enable "intelluxe-$$unit_name"; \
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
			REQUIREMENTS_FILE="requirements.txt"; \
			if [ "$$CI" = "1" ] && [ -f "requirements-ci.txt" ]; then \
				REQUIREMENTS_FILE="requirements-ci.txt"; \
			fi; \
			if [ "$$CI" = "1" ]; then \
				echo "   📋 Installing $$REQUIREMENTS_FILE via uv (user mode)..."; \
				if timeout 120 uv pip install --user -r "$$REQUIREMENTS_FILE" 2>/dev/null; then \
					echo "   ✓ Healthcare requirements installed via uv (user mode)"; \
				else \
					echo "   ⚠️  uv requirements installation failed - falling back to pip"; \
					UV_AVAILABLE=false; \
				fi; \
			else \
				echo "   📋 Installing $$REQUIREMENTS_FILE via uv (system mode)..."; \
				if timeout 120 sudo uv pip install --system --break-system-packages -r "$$REQUIREMENTS_FILE" 2>/dev/null; then \
					echo "   ✓ Healthcare requirements installed via uv (system mode)"; \
				else \
					echo "   ⚠️  uv requirements installation failed - falling back to pip"; \
					UV_AVAILABLE=false; \
				fi; \
			fi; \
		fi; \
	fi; \
	if [ "$$UV_AVAILABLE" = "false" ]; then \
		echo "🐍  Using pip with apt fallbacks for maximum compatibility..."; \
		echo "   📦 Installing system Python tools via apt..."; \
		sudo apt-get update -qq && sudo apt-get install -y python3-pip python3-dev python3-setuptools python3-wheel || true; \
		echo "   🔧 Installing development tools via pip..."; \
		if sudo pip3 install --break-system-packages ruff pyright pytest pytest-asyncio yamllint 2>/dev/null; then \
			echo "   ✓ Development tools installed system-wide"; \
		elif pip3 install --user ruff pyright pytest pytest-asyncio yamllint 2>/dev/null; then \
			echo "   ✓ Development tools installed to user directory"; \
		else \
			echo "   ⚠️  pip installation failed - trying apt packages"; \
			sudo apt-get install -y python3-pytest python3-yaml || true; \
		fi; \
		REQUIREMENTS_FILE="requirements.txt"; \
		if [ "$$CI" = "1" ] && [ -f "requirements-ci.txt" ]; then \
			REQUIREMENTS_FILE="requirements-ci.txt"; \
		fi; \
		if [ -f "$$REQUIREMENTS_FILE" ]; then \
			echo "   📋 Installing $$REQUIREMENTS_FILE via pip..."; \
			if sudo pip3 install --break-system-packages -r "$$REQUIREMENTS_FILE" 2>/dev/null; then \
				echo "   ✓ Healthcare requirements installed system-wide"; \
			elif pip3 install --user -r "$$REQUIREMENTS_FILE" 2>/dev/null; then \
				echo "   ✓ Healthcare requirements installed to user directory"; \
			else \
				echo "   ⚠️  Some requirements may have failed - check individual packages"; \
			fi; \
		fi; \
	fi
	@echo "✅  All development dependencies installed successfully"

clean-cache:
	@echo "🧹  Cleaning package manager caches to free disk space"
	@# Clean uv cache
	@if command -v uv >/dev/null 2>&1; then \
		echo "   🧹 Cleaning uv cache..."; \
		uv cache clean || echo "   ⚠️  uv cache clean failed"; \
	else \
		echo "   ⚠️  uv not found - skipping uv cache cleanup"; \
	fi
	@# Clean pip cache
	@if command -v pip3 >/dev/null 2>&1; then \
		echo "   🧹 Cleaning pip cache..."; \
		pip3 cache purge || echo "   ⚠️  pip cache purge failed"; \
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
	    echo "ERROR: Please specify BACKUP_FILE=path/to/backup.tar.gz"; \
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

# Medical Mirrors Service Commands
medical-mirrors-build:
	@echo "🏗️  Building Medical Mirrors service Docker image"
	@cd services/user/medical-mirrors && docker build -t intelluxe/medical-mirrors:latest .
	@echo "✅ Medical Mirrors Docker image built successfully"

medical-mirrors-rebuild:
	@echo "🔄  Rebuilding Medical Mirrors service (no cache)"
	@cd services/user/medical-mirrors && docker build --no-cache -t intelluxe/medical-mirrors:latest .
	@echo "✅ Medical Mirrors Docker image rebuilt successfully"

medical-mirrors-clean:
	@echo "🧹  Cleaning up Medical Mirrors Docker artifacts"
	@docker images intelluxe/medical-mirrors -q | xargs -r docker rmi -f
	@docker system prune -f --filter "label=service=medical-mirrors"
	@echo "✅ Medical Mirrors Docker cleanup complete"

medical-mirrors-run:
	@echo "🚀  Starting Medical Mirrors service container"
	@docker run -d \
		--name medical-mirrors \
		--network intelluxe-net \
		-p 8080:8080 \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/logs:/app/logs \
		-e PYTHONPATH=/app/src \
		--restart unless-stopped \
		intelluxe/medical-mirrors:latest
	@echo "✅ Medical Mirrors service started on http://localhost:8080"

medical-mirrors-logs:
	@echo "📋  Viewing Medical Mirrors service logs"
	@docker logs -f medical-mirrors

medical-mirrors-stop:
	@echo "🛑  Stopping Medical Mirrors service"
	@docker stop medical-mirrors 2>/dev/null || echo "   ⚠️  Container not running"
	@docker rm medical-mirrors 2>/dev/null || echo "   ⚠️  Container not found"
	@echo "✅ Medical Mirrors service stopped"

medical-mirrors-health:
	@echo "🔍  Checking Medical Mirrors service health"
	@if docker ps --filter "name=medical-mirrors" --filter "status=running" | grep -q medical-mirrors; then \
		echo "   ✅ Container is running"; \
		if curl -f http://localhost:8080/health 2>/dev/null; then \
			echo "   ✅ Health endpoint responding"; \
		else \
			echo "   ⚠️  Health endpoint not responding"; \
		fi; \
	else \
		echo "   ❌ Container not running"; \
	fi

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
		awk '/^[a-zA-Z_][a-zA-Z0-9_]*\(\)/ { func=$$1; line_count=0; start_line=NR } \
		     /^[a-zA-Z_][a-zA-Z0-9_]*\(\)/,/^}/ { \
		         if ($$0 ~ /if.*then|case.*in|for.*do|while.*do/) complexity++; \
		         if ($$0 ~ /^}/) { \
		             if (line_count > 20 || complexity > 5) \
		                 printf "%s:%d: Function %s has %d lines and complexity %d\\n", \
		                        FILENAME, start_line, func, line_count, complexity; \
		             complexity=0 \
		         } \
		         line_count++ \
		     }' "$$script"; \
	done

lint-python:
	@echo "🔍  Running Python lint (ruff and mypy) for healthcare AI components"
	@# Run Ruff for linting (pyproject.toml has exclusions for submodules)
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check .; \
	elif python3 -m ruff --version >/dev/null 2>&1; then \
		python3 -m ruff check .; \
	else \
		python3 -c "import ruff" 2>/dev/null && python3 -m ruff check . || echo "⚠️  Ruff not available"; \
	fi
	@# Run Ruff formatting check
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format --check .; \
	elif python3 -m ruff --version >/dev/null 2>&1; then \
		python3 -m ruff format --check .; \
	else \
		echo "⚠️  Ruff format check skipped"; \
	fi
	@# Run MyPy type checking with error tolerance
	@echo "🔍  Running MyPy type checking (ignore errors during development)"
	@if command -v mypy >/dev/null 2>&1; then \
		mypy . || echo "⚠️  MyPy found issues - run 'mypy .' for details"; \
	else \
		echo "⚠️  MyPy not available"; \
	fi

# Fast development linting - only core healthcare modules
lint-dev:
	@echo "🚀  Running fast development lint (core healthcare modules only)"
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check core/ agents/ config/ --select=E9,F63,F7,F82; \
	else \
		echo "⚠️  Ruff not available for fast lint"; \
	fi

format:
	@echo "🎨  Auto-formatting healthcare AI code"
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format .; \
	elif python3 -m ruff --version >/dev/null 2>&1; then \
		python3 -m ruff format .; \
	else \
		echo "⚠️  Ruff not available for formatting"; \
	fi

validate:
	@echo "🔍  Running comprehensive validation suite"
	$(MAKE) lint
	$(MAKE) test

systemd-verify:
	@echo "🔍  Verifying systemd service configurations"
	@for unit in systemd/*.service systemd/*.timer; do \
	    if [ -f "$$unit" ]; then \
	        echo "   Verifying $$unit..."; \
	        systemd-analyze verify "$$unit" || echo "⚠️  $$unit has issues"; \
	    fi; \
	done

test:
	@echo "🧪  Running healthcare AI test suite"
	@if [ -n "$$CI" ]; then \
		echo "   🤖 CI mode - running tests with coverage"; \
		python3 -m pytest tests/ -v --tb=short --maxfail=5 --disable-warnings; \
	else \
		echo "   🖥️  Development mode - running tests"; \
		python3 -m pytest tests/ -v --tb=short; \
	fi

test-quiet:
	@echo "🧪  Running healthcare AI tests (quiet mode)"
	@python3 -m pytest tests/ -q --disable-warnings

test-coverage:
	@echo "🧪  Running healthcare AI tests with coverage report"
	@python3 -m pytest tests/ --cov=core --cov=agents --cov=config --cov-report=html --cov-report=term-missing

# Synthetic Healthcare Data Generation
data-generate:
	@echo "📊  Generating comprehensive synthetic healthcare dataset"
	python3 scripts/generate_synthetic_healthcare_data.py --doctors 75 --patients 2500 --encounters 6000

data-generate-small:
	@echo "📊  Generating small synthetic healthcare dataset for testing"
	python3 scripts/generate_synthetic_healthcare_data.py --doctors 10 --patients 100 --encounters 200

data-generate-large:
	@echo "📊  Generating large synthetic healthcare dataset for load testing"
	python3 scripts/generate_synthetic_healthcare_data.py --doctors 150 --patients 5000 --encounters 12000

data-clean:
	@echo "🧹  Cleaning synthetic healthcare data"
	@rm -rf data/synthetic/*.json data/synthetic/*.csv
	@echo "✅  Synthetic data cleaned"

data-status:
	@echo "📊  Synthetic healthcare data status"
	@if [ -d "data/synthetic" ]; then \
		echo "   📁 Synthetic data directory exists"; \
		echo "   📄 Files: $$(ls -1 data/synthetic/ 2>/dev/null | wc -l)"; \
		echo "   💾 Size: $$(du -sh data/synthetic/ 2>/dev/null | cut -f1 || echo '0')"; \
	else \
		echo "   ❌ No synthetic data found - run 'make data-generate' to create"; \
	fi

test-ai:
	@echo "🤖  Running healthcare AI evaluation tests"
	python3 -m pytest tests/test_ai_evaluation.py -v --tb=short

test-ai-report:
	@echo "🤖  Running healthcare AI evaluation with detailed report"
	python3 -m pytest tests/test_ai_evaluation.py -v --tb=long --capture=no

# Virtual environment management
venv:
	@echo "🐍  Creating Python virtual environment for healthcare AI"
	@python3 -m venv venv
	@echo "   ✅ Virtual environment created in ./venv/"
	@echo "   💡 Activate with: source venv/bin/activate"
	@echo "   💡 Then run: make deps"

e2e:
	@echo "🔄  Running end-to-end healthcare AI workflow tests"
	@echo "   🚀 Starting services..."
	@bash scripts/bootstrap.sh --dry-run --non-interactive
	@echo "   🧪 Running E2E tests..."
	@python3 -m pytest tests/test_e2e.py -v --tb=short

# Help
help:
	@echo "🏥  Intelluxe AI Healthcare System - Available Commands"
	@echo ""
	@echo "📦  DEPENDENCY MANAGEMENT:"
	@echo "   make deps           - Install all healthcare AI dependencies (CI-aware)"
	@echo "   make update-deps    - Update dependencies to latest versions"
	@echo "   make clean-cache    - Clean package manager caches"
	@echo ""
	@echo "🔧  SETUP & INSTALLATION:"
	@echo "   make install        - Install systemd services and create system users"
	@echo "   make setup          - Interactive healthcare AI stack setup"
	@echo "   make dry-run        - Preview setup without making changes"
	@echo "   make debug          - Debug setup with verbose logging"
	@echo ""
	@echo "🧪  TESTING & VALIDATION:"
	@echo "   make test           - Run healthcare AI test suite"
	@echo "   make test-coverage  - Run tests with coverage report"
	@echo "   make test-ai        - Run AI evaluation tests"
	@echo "   make validate       - Run comprehensive validation (lint + test)"
	@echo "   make e2e            - Run end-to-end workflow tests"
	@echo ""
	@echo "🔍  LINTING & CODE QUALITY:"
	@echo "   make lint           - Run all linting (shell + python)"
	@echo "   make lint-dev       - Fast lint (core modules only)"
	@echo "   make format         - Auto-format code"
	@echo ""
	@echo "📊  SYNTHETIC DATA:"
	@echo "   make data-generate  - Generate comprehensive synthetic healthcare data"
	@echo "   make data-status    - Show synthetic data statistics"
	@echo "   make data-clean     - Remove synthetic data"
	@echo ""
	@echo "🐳  MCP SERVER:"
	@echo "   make mcp           - Build Healthcare MCP server Docker image"
	@echo "   make mcp-rebuild   - Rebuild MCP server (no cache)"
	@echo "   make mcp-clean     - Clean MCP Docker artifacts"
	@echo ""
	@echo "🏥  MEDICAL MIRRORS SERVICE:"
	@echo "   make medical-mirrors-build   - Build Medical Mirrors Docker image"
	@echo "   make medical-mirrors-rebuild - Rebuild Medical Mirrors (no cache)"
	@echo "   make medical-mirrors-run     - Start Medical Mirrors container"
	@echo "   make medical-mirrors-logs    - View Medical Mirrors logs"
	@echo "   make medical-mirrors-stop    - Stop Medical Mirrors service"
	@echo "   make medical-mirrors-health  - Check Medical Mirrors health"
	@echo "   make medical-mirrors-clean   - Clean Medical Mirrors Docker artifacts"
	@echo ""
	@echo "⚙️   SYSTEM MANAGEMENT:"
	@echo "   make diagnostics   - Run comprehensive system diagnostics"
	@echo "   make auto-repair   - Automatically repair unhealthy containers"
	@echo "   make reset         - Reset entire healthcare AI stack"
	@echo "   make teardown      - Complete infrastructure teardown"
	@echo "   make backup        - Backup healthcare VPN configuration"
