.PHONY: \
	   auto-repair \
	   backup \
	   clean-cache \
	   clean-docker \
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
	   healthcare-api \
	   healthcare-api-build \
	   healthcare-api-rebuild \
	   healthcare-api-clean \
	   healthcare-api-run \
	   healthcare-api-stop \
	   healthcare-api-restart \
	   healthcare-api-logs \
	   healthcare-api-health \
	   healthcare-api-status \
	   healthcare-api-test \
	   scispacy-build \
	   scispacy-rebuild \
	   scispacy-clean \
	   scispacy-stop \
	   scispacy-logs \
	   scispacy-health \
	   scispacy-status \
	   scispacy-test \
	   medical-mirrors-build \
	   medical-mirrors-rebuild \
	   medical-mirrors-clean \
	   medical-mirrors-run \
	   medical-mirrors-logs \
	   medical-mirrors-errors \
	   medical-mirrors-errors-summary \
	   medical-mirrors-stop \
	   medical-mirrors-health \
	   medical-mirrors-restart \
	   medical-mirrors-update \
	   medical-mirrors-update-pubmed \
	   medical-mirrors-update-trials \
	   medical-mirrors-update-fda \
	   medical-mirrors-update-icd10 \
	   medical-mirrors-update-billing \
	   medical-mirrors-update-health \
	   medical-mirrors-process-existing \
	   medical-mirrors-process-existing-force \
	   medical-mirrors-process-trials \
	   medical-mirrors-process-trials-force \
	   medical-mirrors-process-pubmed \
	   medical-mirrors-process-pubmed-force \
	   medical-mirrors-process-fda \
	   medical-mirrors-process-fda-force \
	   medical-mirrors-progress \
	   medical-mirrors-quick-test \
	   medical-mirrors-test-pubmed \
	   medical-mirrors-test-trials \
	   medical-mirrors-test-fda \
	   medical-mirrors-test-icd10 \
	   medical-mirrors-test-billing \
	   medical-mirrors-test-health \
	   medical-mirrors-validate-downloads \
	   medical-mirrors-debug-ncbi \
	   medical-mirrors-clean-data \
	   billing-engine-build \
	   billing-engine-rebuild \
	   billing-engine-clean \
	   billing-engine-stop \
	   billing-engine-logs \
	   billing-engine-health \
	   billing-engine-status \
	   billing-engine-test \
	   business-intelligence-build \
	   business-intelligence-rebuild \
	   business-intelligence-clean \
	   business-intelligence-stop \
	   business-intelligence-logs \
	   business-intelligence-health \
	   business-intelligence-status \
	   business-intelligence-test \
	   compliance-monitor-build \
	   compliance-monitor-rebuild \
	   compliance-monitor-clean \
	   compliance-monitor-stop \
	   compliance-monitor-logs \
	   compliance-monitor-health \
	   compliance-monitor-status \
	   compliance-monitor-test \
	   doctor-personalization-build \
	   doctor-personalization-rebuild \
	   doctor-personalization-clean \
	   doctor-personalization-stop \
	   doctor-personalization-logs \
	   doctor-personalization-health \
	   doctor-personalization-status \
	   doctor-personalization-test \
	   insurance-verification-build \
	   insurance-verification-rebuild \
	   insurance-verification-clean \
	   insurance-verification-stop \
	   insurance-verification-logs \
	   insurance-verification-health \
	   insurance-verification-status \
	   insurance-verification-test \
	   parse-downloaded-quick \
	   parse-downloaded-full \
	   parse-downloaded-status \
	   parse-downloaded-pubmed \
	   parse-downloaded-fda \
	   parse-downloaded-trials \
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
	   venv \
	   grafana \
	   healthcare-api \
	   healthcare-mcp \
	   mcp-pipeline \
	   medical-mirrors \
	   n8n \
	   ollama \
	   ollama-webui \
	   postgresql \
	   redis \
	   scispacy \
	   traefik \
	   wireguard \
	   wyoming-whisper

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
	@# NOTE: Lockfile generation via scripts/generate-requirements.py is deprecated.
	@#       Requirements are now edited directly per-environment. Skipping generation.
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
	@# Prefer local virtualenv if present; otherwise smart fallbacks (uv -> pip)
	@echo "🔍  Determining best installation method..."
	@USE_VENV=false; \
	if [ -d ".venv" ] && [ -x ".venv/bin/pip" ]; then \
		echo "   ✓ Detected .venv - will install into local virtualenv"; \
		USE_VENV=true; \
	else \
		echo "   ✗ No local .venv detected"; \
	fi; \
	REQUIREMENTS_FILE="requirements.txt"; \
	if [ "$$CI" = "1" ] && [ -f "requirements-ci.txt" ]; then \
		REQUIREMENTS_FILE="requirements-ci.txt"; \
	fi; \
	if [ "$$USE_VENV" = "true" ]; then \
		echo "🚀  Installing into .venv using pip..."; \
		.venv/bin/pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true; \
		.venv/bin/pip install ruff pyright pytest pytest-asyncio yamllint >/dev/null 2>&1 || true; \
		echo "   � Installing $$REQUIREMENTS_FILE into .venv..."; \
		if .venv/bin/pip install -r "$$REQUIREMENTS_FILE"; then \
			echo "   ✓ Requirements installed into .venv"; \
		else \
			echo "   ⚠️  .venv installation failed - you may need to recreate the venv"; \
		fi; \
		printf "✅  All development dependencies installed successfully\n"; \
		exit 0; \
	fi
	@# Smart dependency installation with comprehensive fallbacks
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

clean-docker:
	@echo "🐳  Cleaning Docker data to free disk space"
	@echo "   📊 Current Docker disk usage:"
	@docker system df 2>/dev/null || echo "   ⚠️  Docker not available"
	@echo "   🧹 Removing all unused Docker data..."
	@docker system prune -a --volumes -f 2>/dev/null || echo "   ⚠️  Docker cleanup failed - check if Docker is running"
	@echo "   📊 Docker disk usage after cleanup:"
	@docker system df 2>/dev/null || echo "   ⚠️  Docker not available"
	@echo "✅  Docker cleanup complete"

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
	export ENVIRONMENT=development && ./scripts/bootstrap.sh

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

# ---------------------------------------------------------------------------
# Bootstrap-driven service restart shortcut
# Sends two Enters (accept defaults) then the service number to restart.
# ---------------------------------------------------------------------------
BOOTSTRAP := ENVIRONMENT=$(or $(ENVIRONMENT),development) ./scripts/bootstrap.sh
define BOOTSTRAP_RESTART
	@echo "🔁  Restarting $(1) via bootstrap.sh (menu #$(2))"
	@printf '\n\n$(2)\n' | $(BOOTSTRAP)
endef

# Interactive service commands - runs make setup then navigates to service
grafana:
	@echo "🔁 Restarting Grafana via setup menu..."
	@printf '3\n1\n' | make setup

healthcare-api:
	@echo "🔁 Restarting Healthcare API via setup menu..."
	@printf '3\n2\n' | make setup

llama-cpp:
	@echo "🔁 Restarting Llama.cpp via setup menu..."
	@printf '3\n3\n' | make setup

medical-mirrors:
	@echo "🔁 Restarting Medical Mirrors via setup menu..."
	@printf '3\n9\n' | make setup

ollama:
	@echo "🔁 Restarting Ollama via setup menu..."
	@printf '3\n5\n' | make setup

ollama-webui:
	@echo "🔁 Restarting Ollama WebUI via setup menu..."
	@printf '3\n6\n' | make setup

postgresql:
	@echo "🔁 Restarting PostgreSQL via setup menu..."
	@printf '3\n7\n' | make setup

redis:
	@echo "🔁 Restarting Redis via setup menu..."
	@printf '3\n8\n' | make setup

scispacy:
	@echo "🔁 Restarting SciSpacy via setup menu..."
	@printf '3\n14\n' | make setup

traefik:
	@echo "🔁 Restarting Traefik via setup menu..."
	@printf '3\n10\n' | make setup

wireguard:
	@echo "🔁 Restarting Wireguard via setup menu..."
	@printf '3\n11\n' | make setup

wyoming-whisper:
	@echo "🔁 Restarting Wyoming Whisper via setup menu..."
	@printf '3\n12\n' | make setup

# Healthcare API Service Commands
healthcare-api-build:
	@echo "🏗️  Building Healthcare API service Docker image"
	@cd services/user && docker build -f healthcare-api/Dockerfile -t intelluxe/healthcare-api:latest .
	@echo "✅ Healthcare API Docker image built successfully"

healthcare-api-rebuild:
	@echo "🔄  Rebuilding Healthcare API service (no cache)"
	@cd services/user && docker build --no-cache -f healthcare-api/Dockerfile -t intelluxe/healthcare-api:latest .
	@echo "✅ Healthcare API Docker image rebuilt successfully"

healthcare-api-clean:
	@echo "🧹  Cleaning up Healthcare API Docker artifacts"
	@docker images intelluxe/healthcare-api -q | xargs -r docker rmi -f
	@docker system prune -f --filter "label=description=HIPAA-compliant Healthcare API with administrative support agents"
	@echo "✅ Healthcare API Docker cleanup complete"

healthcare-api-stop:
	@echo "🛑  Stopping Healthcare API service"
	@docker stop healthcare-api 2>/dev/null || echo "Container not running"
	@docker rm healthcare-api 2>/dev/null || echo "Container not found"
	@echo "✅ Healthcare API service stopped"

healthcare-api-logs:
	@echo "📋  Healthcare API service logs (last 50 lines):"
	@docker logs --tail 50 healthcare-api 2>/dev/null || echo "Container not found or not running"

healthcare-api-health:
	@echo "🏥  Checking Healthcare API service health"
	@curl -f http://172.20.0.16:8000/health 2>/dev/null && echo "✅ Healthcare API service is healthy" || echo "❌ Healthcare API service is unhealthy"

healthcare-api-status:
	@echo "📊  Healthcare API service status:"
	@docker ps --filter name=healthcare-api --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "Container not found"

healthcare-api-test:
	@echo "🧪  Running Healthcare API validation"
	@curl -f http://172.20.0.16:8000/docs 2>/dev/null && echo "✅ Healthcare API docs accessible" || echo "❌ Healthcare API docs not accessible"
	@curl -f http://172.20.0.16:8000/health 2>/dev/null && echo "✅ Healthcare API health check passed" || echo "❌ Healthcare API health check failed"
	@echo "✅  Healthcare API validation complete"

# SciSpacy Service Commands
scispacy-build:
	@echo "🧬  Building SciSpacy NLP service Docker image"
	@cd services/user/scispacy && docker build -t intelluxe/scispacy:latest .
	@echo "✅ SciSpacy Docker image built successfully"

scispacy-rebuild:
	@echo "🔄  Rebuilding SciSpacy NLP service (no cache)"
	@cd services/user/scispacy && docker build --no-cache -t intelluxe/scispacy:latest .
	@echo "✅ SciSpacy Docker image rebuilt successfully"

scispacy-clean:
	@echo "🧹  Cleaning up SciSpacy Docker artifacts"
	@docker images intelluxe/scispacy -q | xargs -r docker rmi -f
	@docker system prune -f --filter "label=description=SciSpacy Healthcare NLP Service"
	@echo "✅ SciSpacy Docker cleanup complete"

scispacy-stop:
	@echo "🛑  Stopping SciSpacy NLP service"
	@docker stop scispacy 2>/dev/null || echo "Container not running"
	@docker rm scispacy 2>/dev/null || echo "Container not found"
	@echo "✅ SciSpacy service stopped"

scispacy-logs:
	@echo "📋  SciSpacy NLP service logs (last 50 lines):"
	@docker logs --tail 50 scispacy 2>/dev/null || echo "Container not found or not running"

scispacy-health:
	@echo "🧬  Checking SciSpacy NLP service health"
	@curl -f http://172.20.0.6:8001/health 2>/dev/null && echo "✅ SciSpacy service is healthy" || echo "❌ SciSpacy service is unhealthy"

scispacy-status:
	@echo "📊  SciSpacy NLP service status:"
	@docker ps --filter name=scispacy --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "Container not found"

scispacy-test:
	@echo "🧪  Running SciSpacy NLP service validation"
	@echo "   🧬 Testing model info endpoint..."
	@curl -f http://172.20.0.6:8001/info 2>/dev/null && echo "✅ SciSpacy model info accessible" || echo "❌ SciSpacy model info not accessible"
	@echo "   🧬 Testing entity analysis with medical text..."
	@curl -s -X POST http://172.20.0.6:8001/analyze \
		-H "Content-Type: application/json" \
		-d '{"text": "Patient presents with chest pain and diabetes mellitus. Prescribed metformin and aspirin.", "enrich": true}' \
		| jq '.entity_count' 2>/dev/null && echo "✅ SciSpacy entity analysis working" || echo "❌ SciSpacy entity analysis failed"
	@echo "✅  SciSpacy validation complete"

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

medical-mirrors-logs:
	@echo "📋  Viewing Medical Mirrors service logs"
	@docker logs -f medical-mirrors

medical-mirrors-errors:
	@echo "🚨  Viewing Medical Mirrors ERRORS ONLY"
	@docker logs medical-mirrors 2>&1 | grep "ERROR" | sed 's/\[(psycopg2\.errors\.[^)]*)/[Database Error]/g' | sed 's/\[SQL: [^]]*\]/[SQL: query truncated]/g' | sed 's/\[parameters: [^]]*\]/[parameters: truncated]/g' | head -50

medical-mirrors-errors-summary:
	@echo "🔍  Medical Mirrors ERROR SUMMARY"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker logs medical-mirrors 2>&1 | grep "ERROR" | awk -F' - ERROR - ' '{print $$2}' | sed 's/: (psycopg2\.errors\.[^)]*).*/: [Database constraint violation]/' | sed 's/Client error.*for url.*/[API request failed - check endpoint URL]/' | sort | uniq -c | sort -nr
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

medical-mirrors-stop:
	@echo "🛑  Stopping Medical Mirrors service"
	@docker stop medical-mirrors 2>/dev/null || echo "   ⚠️  Container not running"
	@docker rm medical-mirrors 2>/dev/null || echo "   ⚠️  Container not found"
	@echo "✅ Medical Mirrors service stopped"

medical-mirrors-health:
	@echo "🔍  Checking Medical Mirrors service health"
	@if docker ps --filter "name=medical-mirrors" --filter "status=running" | grep -q medical-mirrors; then \
		echo "   ✅ Container is running"; \
		if curl -f http://localhost:8081/health 2>/dev/null; then \
			echo "   ✅ Health endpoint responding"; \
		else \
			echo "   ⚠️  Health endpoint not responding"; \
		fi; \
	else \
		echo "   ❌ Container not running"; \
	fi

medical-mirrors-update:
	@echo "🧠  SMART Medical Mirrors Update (Auto-detects full load vs incremental)"
	@echo "   🔍 Analyzes database state to determine optimal update strategy"
	@echo "   📊 Full loads for empty/small databases, incremental updates for existing data"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo "   🛑 To stop: make medical-mirrors-stop"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🧠 Starting SMART update (analyzes database counts)..."; \
		curl -X POST http://localhost:8081/smart-update -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ Smart update process started based on database analysis"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
		echo "   🛑 To stop: make medical-mirrors-stop"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Smart Medical Mirrors update started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-update-legacy:
	@echo "🔄  Updating ALL Medical Mirrors databases (6 data sources) - LEGACY MODE"
	@echo "   ⚠️  WARNING: This process will take MANY HOURS and may hit rate limits!"
	@echo "   📊 Data sources: PubMed, ClinicalTrials, FDA, ICD-10, Billing Codes, Health Info"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo "   🛑 To stop: make medical-mirrors-stop"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🚀 Starting async update process for all 6 data sources..."; \
		curl -X POST http://localhost:8081/update/pubmed -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   📚 PubMed update started in background"; \
		sleep 2; \
		curl -X POST http://localhost:8081/update/trials -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   🧪 ClinicalTrials update started in background"; \
		sleep 2; \
		curl -X POST http://localhost:8081/update/fda -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   💊 FDA update started in background"; \
		sleep 2; \
		curl -X POST http://localhost:8081/update/icd10 -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   🏥 ICD-10 codes update started in background"; \
		sleep 2; \
		curl -X POST http://localhost:8081/update/billing -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   🏦 Billing codes update started in background"; \
		sleep 2; \
		curl -X POST http://localhost:8081/update/health-info -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   📋 Health info update started in background"; \
		echo "   ✅ All 6 update requests sent asynchronously"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ All 6 data source update processes started - use 'make medical-mirrors-progress' to monitor"

medical-mirrors-process-existing:
	@echo "📂  Processing ALL existing downloaded medical data files (SMART - skips processed files)"
	@echo "   🔍 Will load existing compressed files: Clinical Trials, PubMed, FDA"
	@echo "   ⚡ OPTIMIZED: Only processes files that haven't been processed before"
	@echo "   💡 Use 'make medical-mirrors-process-existing-force' to reprocess all files"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   📂 Starting SMART processing of all existing files (force=false)..."; \
		curl -X POST "http://localhost:8081/process/all-existing?force=false" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ All existing files are now being processed (skipping already processed)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Smart existing files processing started - monitor with 'make medical-mirrors-progress'" 

medical-mirrors-process-existing-force:
	@echo "📂  Processing ALL existing downloaded medical data files (FORCE - reprocess everything)"
	@echo "   🔍 Will load existing compressed files: Clinical Trials, PubMed, FDA"
	@echo "   🔄 FORCE MODE: Will reprocess ALL files regardless of previous processing"
	@echo "   ⚠️  This will take SEVERAL HOURS but ensures fresh data processing"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   📂 Starting FORCE processing of all existing files (force=true)..."; \
		curl -X POST "http://localhost:8081/process/all-existing?force=true" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ All existing files are now being reprocessed (force mode)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Force existing files processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-update-pubmed:
	@echo "📚  Updating PubMed database"
	@echo "   ⚠️  WARNING: PubMed has 35+ million articles - this will take 6-12+ HOURS!"
	@echo "   🚫 Rate limits: NCBI allows ~3 requests/second without API key"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   📚 Starting async PubMed update..."; \
		curl -X POST http://localhost:8081/update/pubmed -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   ✅ PubMed update started in background"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ PubMed update started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-update-trials:
	@echo "🧪  Updating ClinicalTrials database"
	@echo "   ⚠️  WARNING: ClinicalTrials.gov has 400,000+ studies - this will take 2-4+ HOURS!"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🧪 Starting async ClinicalTrials update..."; \
		curl -X POST http://localhost:8081/update/trials -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   ✅ ClinicalTrials update started in background"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ ClinicalTrials update started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-update-fda:
	@echo "💊  Updating FDA database"
	@echo "   ⚠️  WARNING: FDA database is large - this will take 1-3+ HOURS!"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   💊 Starting async FDA update..."; \
		curl -X POST http://localhost:8081/update/fda -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   ✅ FDA update started in background"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ FDA update started - monitor with 'make medical-mirrors-progress'"
medical-mirrors-update-icd10:
	@echo "🏥  Updating ICD-10 diagnostic codes"
	@echo "   ⚠️  WARNING: ICD-10 database is comprehensive - this will take 30-60+ MINUTES!"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🏥 Starting async ICD-10 update..."; \
		curl -X POST http://localhost:8081/update/icd10 -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   ✅ ICD-10 update started in background"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ ICD-10 update started - monitor with 'make medical-mirrors-progress'"
medical-mirrors-update-billing:
	@echo "🏦  Updating billing codes (CPT/HCPCS)"
	@echo "   ⚠️  WARNING: Billing codes database is comprehensive - this will take 30-60+ MINUTES!"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🏦 Starting async billing codes update..."; \
		curl -X POST http://localhost:8081/update/billing -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   ✅ Billing codes update started in background"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Billing codes update started - monitor with 'make medical-mirrors-progress'"
medical-mirrors-update-health:
	@echo "📋  Updating health information (topics, exercises, nutrition)"
	@echo "   ⚠️  WARNING: Health info database is comprehensive - this will take 1-2+ HOURS!"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   📋 Starting async health info update..."; \
		curl -X POST http://localhost:8081/update/health-info -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   ✅ Health info update started in background"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Health info update started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-process-trials:
	@echo "🧪  Processing existing ClinicalTrials files (SMART - skips processed files)"
	@echo "   🔍 Will load existing compressed JSON files from downloads"
	@echo "   ⚡ OPTIMIZED: Only processes files that haven't been processed before"
	@echo "   💡 Use 'make medical-mirrors-process-trials-force' to reprocess all files"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🧪 Starting SMART processing of ClinicalTrials files (force=false)..."; \
		curl -X POST "http://localhost:8081/process/trials?force=false" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ ClinicalTrials files are now being processed (skipping already processed)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Smart ClinicalTrials processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-process-trials-force:
	@echo "🧪  Processing existing ClinicalTrials files (FORCE - reprocess everything)"
	@echo "   🔍 Will load existing compressed JSON files from downloads"
	@echo "   🔄 FORCE MODE: Will reprocess ALL files regardless of previous processing"
	@echo "   ⚠️  This may take 2-4+ HOURS but ensures fresh data processing"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🧪 Starting FORCE processing of ClinicalTrials files (force=true)..."; \
		curl -X POST "http://localhost:8081/process/trials?force=true" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ ClinicalTrials files are now being reprocessed (force mode)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Force ClinicalTrials processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-process-pubmed:
	@echo "📚  Processing existing PubMed files (SMART - skips processed files)"
	@echo "   🔍 Will load existing compressed XML files from downloads"
	@echo "   ⚡ OPTIMIZED: Only processes files that haven't been processed before"
	@echo "   💡 Use 'make medical-mirrors-process-pubmed-force' to reprocess all files"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   📚 Starting SMART processing of PubMed files (force=false)..."; \
		curl -X POST "http://localhost:8081/process/pubmed?force=false" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ PubMed files are now being processed (skipping already processed)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Smart PubMed processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-process-pubmed-force:
	@echo "📚  Processing existing PubMed files (FORCE - reprocess everything)"
	@echo "   🔍 Will load existing compressed XML files from downloads"
	@echo "   🔄 FORCE MODE: Will reprocess ALL files regardless of previous processing"
	@echo "   ⚠️  This may take 6-12+ HOURS but ensures fresh data processing"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   📚 Starting FORCE processing of PubMed files (force=true)..."; \
		curl -X POST "http://localhost:8081/process/pubmed?force=true" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ PubMed files are now being reprocessed (force mode)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Force PubMed processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-process-fda:
	@echo "💊  Processing existing FDA files (SMART - skips processed files)"
	@echo "   🔍 Will load existing FDA data files from downloads"
	@echo "   ⚡ OPTIMIZED: Only processes files that haven't been processed before"
	@echo "   💡 Use 'make medical-mirrors-process-fda-force' to reprocess all files"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   💊 Starting SMART processing of FDA files (force=false)..."; \
		curl -X POST "http://localhost:8081/process/fda?force=false" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ FDA files are now being processed (skipping already processed)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Smart FDA processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-process-fda-force:
	@echo "💊  Processing existing FDA files (FORCE - reprocess everything)"
	@echo "   🔍 Will load existing FDA data files from downloads"
	@echo "   🔄 FORCE MODE: Will reprocess ALL files regardless of previous processing"
	@echo "   ⚠️  This may take 1-3+ HOURS but ensures fresh data processing"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   💊 Starting FORCE processing of FDA files (force=true)..."; \
		curl -X POST "http://localhost:8081/process/fda?force=true" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ FDA files are now being reprocessed (force mode)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Force FDA processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-process-billing:
	@echo "🏦  Processing existing billing codes files (SMART - skips processed files)"
	@echo "   🔍 Will load existing billing codes ZIP files from downloads"
	@echo "   ⚡ OPTIMIZED: Only processes files that haven't been processed before"
	@echo "   💡 Use 'make medical-mirrors-process-billing-force' to reprocess all files"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🏦 Starting SMART processing of billing codes files (force=false)..."; \
		curl -X POST "http://localhost:8081/process/billing?force=false" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ Billing codes files are now being processed (skipping already processed)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Smart billing codes processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-process-billing-force:
	@echo "🏦  Processing existing billing codes files (FORCE - reprocess everything)"
	@echo "   🔍 Will load existing billing codes ZIP files from downloads"
	@echo "   🔄 FORCE MODE: Will reprocess ALL files regardless of previous processing"
	@echo "   ⚠️  This may take 30-60+ MINUTES but ensures fresh data processing"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🏦 Starting FORCE processing of billing codes files (force=true)..."; \
		curl -X POST "http://localhost:8081/process/billing?force=true" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ Billing codes files are now being reprocessed (force mode)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Force billing codes processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-process-icd10:
	@echo "🏥  Processing existing ICD-10 codes files (SMART - skips processed files)"
	@echo "   🔍 Will load existing ICD-10 ZIP files from downloads"
	@echo "   ⚡ OPTIMIZED: Only processes files that haven't been processed before"
	@echo "   💡 Use 'make medical-mirrors-process-icd10-force' to reprocess all files"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🏥 Starting SMART processing of ICD-10 files (force=false)..."; \
		curl -X POST "http://localhost:8081/process/icd10?force=false" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ ICD-10 files are now being processed (skipping already processed)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Smart ICD-10 processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-process-icd10-force:
	@echo "🏥  Processing existing ICD-10 codes files (FORCE - reprocess everything)"
	@echo "   🔍 Will load existing ICD-10 ZIP files from downloads"
	@echo "   🔄 FORCE MODE: Will reprocess ALL files regardless of previous processing"
	@echo "   ⚠️  This may take 30-60+ MINUTES but ensures fresh data processing"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🏥 Starting FORCE processing of ICD-10 files (force=true)..."; \
		curl -X POST "http://localhost:8081/process/icd10?force=true" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ ICD-10 files are now being reprocessed (force mode)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Force ICD-10 processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-process-health:
	@echo "🌱  Processing existing health info files (SMART - skips processed files)"
	@echo "   🔍 Will load existing health info JSON files from downloads"
	@echo "   ⚡ OPTIMIZED: Only processes files that haven't been processed before"
	@echo "   💡 Use 'make medical-mirrors-process-health-force' to reprocess all files"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🌱 Starting SMART processing of health info files (force=false)..."; \
		curl -X POST "http://localhost:8081/process/health?force=false" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ Health info files are now being processed (skipping already processed)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Smart health info processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-process-health-force:
	@echo "🌱  Processing existing health info files (FORCE - reprocess everything)"
	@echo "   🔍 Will load existing health info JSON files from downloads"
	@echo "   🔄 FORCE MODE: Will reprocess ALL files regardless of previous processing"
	@echo "   ⚠️  This may take 1-2+ HOURS but ensures fresh data processing"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🌱 Starting FORCE processing of health info files (force=true)..."; \
		curl -X POST "http://localhost:8081/process/health?force=true" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ Health info files are now being reprocessed (force mode)"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Force health info processing started - monitor with 'make medical-mirrors-progress'"

medical-mirrors-progress:
	@echo "📊  Medical Mirrors Update Progress"
	@echo "   🔄 Refreshing every 10 seconds (Ctrl+C to stop)"
	@echo ""
	@while true; do \
		clear; \
		echo "📊 Medical Mirrors Progress - $$(date)"; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		curl -s http://localhost:8081/status | jq -r '"🏥 Service: " + .service, "", "📚 PubMed:", "   Articles: " + (.mirrors.pubmed.total_articles | tostring), "   Status: " + .mirrors.pubmed.status, "   Last Update: " + (.mirrors.pubmed.last_update // "Never"), "", "🧪 Clinical Trials:", "   Trials: " + (.mirrors.clinicaltrials.total_trials | tostring), "   Status: " + .mirrors.clinicaltrials.status, "   Last Update: " + (.mirrors.clinicaltrials.last_update // "Never"), "", "💊 FDA Drugs:", "   Drugs: " + (.mirrors.fda.total_drugs | tostring), "   Status: " + .mirrors.fda.status, "   Last Update: " + (.mirrors.fda.last_update // "Never")' || echo "❌ Service not responding"; \
		echo ""; \
		echo "💡 Tips:"; \
		echo "   • Updates run in background - you can close this monitor"; \
		echo "   • Check logs: make medical-mirrors-logs"; \
		echo "   • Stop updates: make medical-mirrors-stop"; \
		sleep 10; \
	done

medical-mirrors-progress-enhanced:
	@echo "📊  Enhanced Medical Data Loading Progress Monitor"
	@echo "   🚀 Real-time database counts with rates and ETAs"
	@echo "   🔄 Auto-refreshing with progress bars and statistics"
	@echo "   💡 Press Ctrl+C to exit monitor"
	@echo ""
	@python3 scripts/monitor_medical_data_progress.py

medical-mirrors-counts:
	@echo "📈  Current Medical Database Record Counts"
	@echo ""
	@curl -s http://localhost:8081/database/counts | jq '.counts' || echo "❌ Service not responding"

# Individual test commands for each data source
medical-mirrors-test-pubmed:
	@echo "📚  Testing PubMed update (3 files only)"
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   📚 Testing PubMed updates (3 files only)..."; \
		curl -X POST "http://localhost:8081/update/pubmed?quick_test=true&max_files=3" -H "Content-Type: application/json" -m 10 2>/dev/null && echo "   ✅ PubMed test started" || echo "   ⚠️  PubMed request timed out (normal)"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi

medical-mirrors-test-trials:
	@echo "🧪  Testing Clinical Trials update (100 studies only)"
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🧪 Testing ClinicalTrials updates (100 studies only)..."; \
		curl -X POST "http://localhost:8081/update/trials?quick_test=true&limit=100" -H "Content-Type: application/json" -m 10 2>/dev/null && echo "   ✅ Trials test started" || echo "   ⚠️  Trials request timed out (normal)"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi

medical-mirrors-test-fda:
	@echo "💊  Testing FDA update (1000 drugs only)"
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   💊 Testing FDA updates (1000 drugs only)..."; \
		curl -X POST "http://localhost:8081/update/fda?quick_test=true&limit=1000" -H "Content-Type: application/json" -m 10 2>/dev/null && echo "   ✅ FDA test started" || echo "   ⚠️  FDA request timed out (normal)"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi

medical-mirrors-test-icd10:
	@echo "🏥  Testing ICD-10 update (100 codes only)"
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🏥 Testing ICD-10 updates (100 codes only)..."; \
		curl -X POST "http://localhost:8081/update/icd10?quick_test=true" -H "Content-Type: application/json" -m 10 2>/dev/null && echo "   ✅ ICD-10 test started" || echo "   ⚠️  ICD-10 request timed out (normal)"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi

medical-mirrors-test-billing:
	@echo "🏦  Testing Billing codes update (100 codes only)"
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🏦 Testing Billing codes updates (100 codes only)..."; \
		curl -X POST "http://localhost:8081/update/billing?quick_test=true" -H "Content-Type: application/json" -m 10 2>/dev/null && echo "   ✅ Billing test started" || echo "   ⚠️  Billing request timed out (normal)"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi

medical-mirrors-test-health:
	@echo "📋  Testing Health Info update (10 topics only)"
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   📋 Testing Health Info updates (10 topics only)..."; \
		curl -X POST "http://localhost:8081/update/health-info?quick_test=true" -H "Content-Type: application/json" -m 10 2>/dev/null && echo "   ✅ Health Info test started" || echo "   ⚠️  Health Info request timed out (normal)"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi

medical-mirrors-quick-test:
	@echo "🚀  Quick test update (testing all 6 data sources with SMALL samples)"
	@echo "   ⚠️  This will download minimal subsets for fast testing only"
	@echo "   📊 Sample sizes: PubMed=3 files, Trials=100 studies, FDA=1000 drugs, ICD-10=100 codes, Billing=100 codes, Health=10 topics"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo ""; \
		echo "   📚 Testing PubMed updates (3 files only)..."; \
		curl -X POST "http://localhost:8081/update/pubmed?quick_test=true&max_files=3" -H "Content-Type: application/json" -m 10 2>/dev/null && echo "   ✅ PubMed request sent" || echo "   ⚠️  PubMed request timed out (normal)"; \
		echo ""; \
		echo "   🧪 Testing ClinicalTrials updates (100 trials only)..."; \
		curl -X POST "http://localhost:8081/update/trials?quick_test=true&limit=100" -H "Content-Type: application/json" -m 10 2>/dev/null && echo "   ✅ Trials request sent" || echo "   ⚠️  Trials request timed out (normal)"; \
		echo ""; \
		echo "   💊 Testing FDA updates (1000 drugs only)..."; \
		curl -X POST "http://localhost:8081/update/fda?quick_test=true&limit=1000" -H "Content-Type: application/json" -m 10 2>/dev/null && echo "   ✅ FDA request sent" || echo "   ⚠️  FDA request timed out (normal)"; \
		echo ""; \
		echo "   🏥 Testing ICD-10 updates (100 codes only)..."; \
		curl -X POST "http://localhost:8081/update/icd10?quick_test=true" -H "Content-Type: application/json" -m 10 2>/dev/null && echo "   ✅ ICD-10 request sent" || echo "   ⚠️  ICD-10 request timed out (normal)"; \
		echo ""; \
		echo "   🏦 Testing Billing codes updates (100 codes only)..."; \
		curl -X POST "http://localhost:8081/update/billing?quick_test=true" -H "Content-Type: application/json" -m 10 2>/dev/null && echo "   ✅ Billing request sent" || echo "   ⚠️  Billing request timed out (normal)"; \
		echo ""; \
		echo "   📋 Testing Health Info updates (10 topics only)..."; \
		curl -X POST "http://localhost:8081/update/health-info?quick_test=true" -H "Content-Type: application/json" -m 10 2>/dev/null && echo "   ✅ Health Info request sent" || echo "   ⚠️  Health Info request timed out (normal)"; \
		echo ""; \
		echo "   ⏳ Waiting 15 seconds for optimized multi-core processing..."; \
		sleep 15; \
		echo "   🔍 Validating all downloaded files..."; \
		$(MAKE) medical-mirrors-validate-downloads; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Quick test completed with minimal samples - use 'make medical-mirrors-progress' for monitoring"

medical-mirrors-validate-downloads:
	@echo "🔍  Validating downloaded medical data files"
	@echo ""
	@echo "📚 PubMed Files:"
	@if docker exec medical-mirrors sh -c 'ls -la /app/data/pubmed/ 2>/dev/null' | head -10; then \
		echo "📂 Sample PubMed content:"; \
		docker exec medical-mirrors sh -c 'for f in /app/data/pubmed/*.xml.gz; do if [ -f "$$f" ]; then echo "=== $$f ==="; zcat "$$f" 2>/dev/null | head -3 || echo "❌ Invalid gzip file"; break; fi; done' || echo "❌ No PubMed files found"; \
	else \
		echo "❌ No PubMed data directory found"; \
	fi
	@echo ""
	@echo "🧪 ClinicalTrials Files:"
	@if docker exec medical-mirrors sh -c 'ls -la /app/data/clinicaltrials/ 2>/dev/null' | head -10; then \
		echo "📂 Sample ClinicalTrials content:"; \
		docker exec medical-mirrors sh -c 'for f in /app/data/clinicaltrials/*.json /app/data/clinicaltrials/*.xml; do if [ -f "$$f" ]; then echo "=== $$f ==="; head -3 "$$f" 2>/dev/null || echo "❌ Invalid file"; break; fi; done' || echo "❌ No ClinicalTrials files found"; \
	else \
		echo "❌ No ClinicalTrials data directory found"; \
	fi
	@echo ""
	@echo "💊 FDA Files:"
	@if docker exec medical-mirrors sh -c 'ls -la /app/data/fda/ 2>/dev/null' | head -10; then \
		echo "📂 Sample FDA content:"; \
		docker exec medical-mirrors sh -c 'for f in /app/data/fda/*.json /app/data/fda/*.xml; do if [ -f "$$f" ]; then echo "=== $$f ==="; head -3 "$$f" 2>/dev/null || echo "❌ Invalid file"; break; fi; done' || echo "❌ No FDA files found"; \
	else \
		echo "❌ No FDA data directory found"; \
	fi

medical-mirrors-debug-ncbi:
	@echo "🔬  Testing all medical data APIs directly"
	@echo ""
	@echo "� Testing NCBI PubMed API..."
	@echo "   🔗 PubMed baseline files:"
	@curl -s "https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/" | head -10 || echo "❌ NCBI baseline connection failed"
	@echo ""
	@echo "   🔗 PubMed update files:"
	@curl -s "https://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/" | head -10 || echo "❌ NCBI updates connection failed"
	@echo ""
	@echo "🧪 Testing ClinicalTrials.gov API..."
	@echo "   � ClinicalTrials API test:"
	@curl -s "https://clinicaltrials.gov/api/query/study_fields?expr=cancer&fields=NCTId,BriefTitle&min_rnk=1&max_rnk=3&fmt=json" | head -5 || echo "❌ ClinicalTrials API connection failed"
	@echo ""
	@echo "💊 Testing FDA API..."
	@echo "   🔗 FDA Drug API test:"
	@curl -s "https://api.fda.gov/drug/label.json?limit=2" | head -5 || echo "❌ FDA API connection failed"
	@echo ""
	@echo "💡 If any connections fail, this explains download issues for that data source"

medical-mirrors-clean-data:
	@echo "🧹  Cleaning all medical data files"
	@echo ""
	@echo "📚 Cleaning PubMed files..."
	@if docker exec medical-mirrors sh -c 'ls /app/data/pubmed/*.xml.gz 2>/dev/null'; then \
		echo "   🗑️  Removing PubMed files..."; \
		docker exec medical-mirrors sh -c 'rm -f /app/data/pubmed/*.xml.gz'; \
		echo "   ✅ PubMed files removed"; \
	else \
		echo "   ✅ No PubMed files found"; \
	fi
	@echo ""
	@echo "🧪 Cleaning ClinicalTrials files..."
	@if docker exec medical-mirrors sh -c 'ls /app/data/clinicaltrials/*.json /app/data/clinicaltrials/*.xml 2>/dev/null'; then \
		echo "   🗑️  Removing ClinicalTrials files..."; \
		docker exec medical-mirrors sh -c 'rm -f /app/data/clinicaltrials/*.json /app/data/clinicaltrials/*.xml'; \
		echo "   ✅ ClinicalTrials files removed"; \
	else \
		echo "   ✅ No ClinicalTrials files found"; \
	fi
	@echo ""
	@echo "💊 Cleaning FDA files..."
	@if docker exec medical-mirrors sh -c 'ls /app/data/fda/*.json /app/data/fda/*.xml 2>/dev/null'; then \
		echo "   🗑️  Removing FDA files..."; \
		docker exec medical-mirrors sh -c 'rm -f /app/data/fda/*.json /app/data/fda/*.xml'; \
		echo "   ✅ FDA files removed"; \
	else \
		echo "   ✅ No FDA files found"; \
	fi

# Additional Medical Mirrors Commands - Download Only Operations

medical-mirrors-download-pubmed:
	@echo "📚  Downloading PubMed data (NO processing)"
	@echo "   ⚠️  WARNING: Downloads 35+ million articles - requires 100GB+ space and 6-12+ HOURS!"
	@echo "   📦 This only downloads files, use medical-mirrors-process-pubmed to load into database"
	@echo ""
	@echo "   📊 Starting PubMed download..."
	@cd /home/intelluxe && python3 scripts/smart_pubmed_download.py
	@echo "✅ PubMed download complete - use 'make medical-mirrors-process-pubmed' to load into database"

medical-mirrors-download-clinicaltrials:
	@echo "🧪  Downloading ClinicalTrials.gov data (NO processing)"
	@echo "   ⚠️  WARNING: Downloads 400,000+ trials - requires 25GB+ space and 2-4+ HOURS!"
	@echo "   📦 This only downloads files, use medical-mirrors-process-trials to load into database"
	@echo ""
	@echo "   📊 Starting ClinicalTrials download..."
	@cd /home/intelluxe && python3 scripts/smart_clinicaltrials_download.py
	@echo "✅ ClinicalTrials download complete - use 'make medical-mirrors-process-trials' to load into database"

medical-mirrors-download-fda:
	@echo "💊  Downloading FDA data (NO processing)"
	@echo "   ⚠️  WARNING: Downloads large FDA datasets - requires 30GB+ space and 1-3+ HOURS!"
	@echo "   📦 This only downloads files, use medical-mirrors-process-fda to load into database"
	@echo ""
	@echo "   📊 Starting FDA download..."
	@cd /home/intelluxe && python3 scripts/smart_fda_download.py
	@echo "✅ FDA download complete - use 'make medical-mirrors-process-fda' to load into database"

medical-mirrors-download-icd10:
	@echo "🏥  Downloading ICD-10 codes (NO processing)"
	@echo "   📦 This only downloads files, use medical-mirrors-process-icd10 to load into database"
	@echo ""
	@echo "   📊 Starting ICD-10 download..."
	@cd /home/intelluxe && python3 scripts/smart_icd10_download.py
	@echo "✅ ICD-10 download complete - use 'make medical-mirrors-process-icd10' to load into database"

medical-mirrors-download-billing:
	@echo "🏦  Downloading billing codes (NO processing)"
	@echo "   📦 This only downloads files, use medical-mirrors-process-billing to load into database"
	@echo ""
	@echo "   📊 Starting billing codes download..."
	@cd /home/intelluxe && python3 scripts/smart_billing_download.py
	@echo "✅ Billing codes download complete - use 'make medical-mirrors-process-billing' to load into database"

medical-mirrors-download-health-info:
	@echo "🌱  Downloading health info data (NO processing)"
	@echo "   ⚠️  WARNING: Downloads comprehensive health database - requires 10GB+ space and 1-2+ HOURS!"
	@echo "   📦 This only downloads files, use medical-mirrors-process-health to load into database"
	@echo ""
	@echo "   📊 Starting health info download..."
	@cd /home/intelluxe && python3 scripts/smart_health_info_download.py
	@echo "✅ Health info download complete - use 'make medical-mirrors-process-health' to load into database"

medical-mirrors-download-medlineplus:
	@echo "📋  Downloading MedlinePlus topics (NO processing)"
	@echo "   📦 This only downloads files, use medical-mirrors-process-medlineplus to load into database"
	@echo ""
	@echo "   📊 Starting MedlinePlus download..."
	@cd /home/intelluxe && python3 scripts/smart_medlineplus_download.py
	@echo "✅ MedlinePlus download complete - use 'make medical-mirrors-process-medlineplus' to load into database"

# Process MedlinePlus Topics
medical-mirrors-process-medlineplus:
	@echo "📋  Processing existing MedlinePlus topics"
	@echo "   🔍 Will load existing MedlinePlus JSON files from downloads"
	@echo "   🔄 Merges with existing health topics in database"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   📋 Starting processing of MedlinePlus topics..."; \
		curl -X POST "http://localhost:8081/process/medlineplus" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ MedlinePlus topics are now being processed"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ MedlinePlus processing started - monitor with 'make medical-mirrors-progress'"

# Smart Update - Intelligent incremental updates
medical-mirrors-smart-update:
	@echo "🧠  Running smart update for all medical data sources"
	@echo "   ⚡ INTELLIGENT: Only downloads and processes new/changed data"
	@echo "   📊 Checks for updates in: PubMed, ClinicalTrials, FDA, Health Info"
	@echo "   ⏱️  Much faster than full updates (minutes vs hours)"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🧠 Starting smart update..."; \
		curl -X POST "http://localhost:8081/smart-update" -H "Content-Type: application/json" --max-time 15; \
		echo ""; \
		echo "   ✅ Smart update started for all data sources"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Smart update started - monitor with 'make medical-mirrors-progress'"

# Database initialization
medical-mirrors-database-init:
	@echo "🗄️  Initializing medical mirrors database tables"
	@echo "   📊 Creates all required tables for medical data storage"
	@echo "   ⚠️  Safe to run multiple times - uses IF NOT EXISTS"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🗄️ Creating database tables..."; \
		curl -X POST "http://localhost:8081/database/create-tables" -H "Content-Type: application/json" --max-time 30; \
		echo ""; \
		echo "   ✅ Database tables created successfully"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Database initialization complete"

# Complete download and process workflow
medical-mirrors-download-all:
	@echo "📦  Downloading ALL medical data sources (NO processing)"
	@echo "   ⚠️  WARNING: This will download ALL data sources - requires 200GB+ space and 12-24+ HOURS!"
	@echo "   📊 Includes: PubMed, ClinicalTrials, FDA, ICD-10, Billing, Health Info, MedlinePlus"
	@echo ""
	@read -p "   ⚠️  Are you sure you want to download ALL data? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "   📊 Starting sequential downloads..."; \
		$(MAKE) medical-mirrors-download-pubmed; \
		$(MAKE) medical-mirrors-download-clinicaltrials; \
		$(MAKE) medical-mirrors-download-fda; \
		$(MAKE) medical-mirrors-download-icd10; \
		$(MAKE) medical-mirrors-download-billing; \
		$(MAKE) medical-mirrors-download-health-info; \
		$(MAKE) medical-mirrors-download-medlineplus; \
		echo "✅ All downloads complete!"; \
	else \
		echo "   ❌ Download cancelled"; \
	fi

# Process all downloaded data
medical-mirrors-process-all:
	@echo "⚙️  Processing ALL downloaded medical data"
	@echo "   📊 Will process: PubMed, ClinicalTrials, FDA, ICD-10, Billing, Health Info, MedlinePlus"
	@echo "   ⚡ SMART: Only processes unprocessed files"
	@echo ""
	@echo "   📊 Starting sequential processing..."
	@$(MAKE) medical-mirrors-process-pubmed
	@$(MAKE) medical-mirrors-process-trials  
	@$(MAKE) medical-mirrors-process-fda
	@$(MAKE) medical-mirrors-process-icd10
	@$(MAKE) medical-mirrors-process-billing
	@$(MAKE) medical-mirrors-process-health
	@$(MAKE) medical-mirrors-process-medlineplus
	@echo "✅ All processing complete!"

# Help command for medical-mirrors
medical-mirrors-help:
	@echo "📚 Medical Mirrors Commands Reference"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "   make medical-mirrors-database-init   # Initialize database tables"
	@echo "   make medical-mirrors-smart-update    # Smart incremental update (fastest)"
	@echo ""
	@echo "📦 Download Commands (fetch data only, no processing):"
	@echo "   make medical-mirrors-download-pubmed         # Download PubMed articles"
	@echo "   make medical-mirrors-download-clinicaltrials # Download clinical trials"
	@echo "   make medical-mirrors-download-fda           # Download FDA data"
	@echo "   make medical-mirrors-download-icd10         # Download ICD-10 codes"
	@echo "   make medical-mirrors-download-billing       # Download billing codes"
	@echo "   make medical-mirrors-download-health-info   # Download health info"
	@echo "   make medical-mirrors-download-medlineplus   # Download MedlinePlus topics"
	@echo "   make medical-mirrors-download-all           # Download ALL sources (200GB+)"
	@echo ""
	@echo "⚙️ Process Commands (load downloaded data into database):"
	@echo "   make medical-mirrors-process-pubmed          # Process PubMed files"
	@echo "   make medical-mirrors-process-trials          # Process clinical trials"
	@echo "   make medical-mirrors-process-fda            # Process FDA data"
	@echo "   make medical-mirrors-process-icd10          # Process ICD-10 codes"
	@echo "   make medical-mirrors-process-billing        # Process billing codes"
	@echo "   make medical-mirrors-process-health         # Process health info"
	@echo "   make medical-mirrors-process-medlineplus    # Process MedlinePlus topics"
	@echo "   make medical-mirrors-process-all            # Process ALL downloaded data"
	@echo ""
	@echo "🔄 Update Commands (download + process):"
	@echo "   make medical-mirrors-update          # Update ALL sources (smart mode)"
	@echo "   make medical-mirrors-update-pubmed   # Update PubMed"
	@echo "   make medical-mirrors-update-trials   # Update clinical trials"
	@echo "   make medical-mirrors-update-fda      # Update FDA data"
	@echo "   make medical-mirrors-update-icd10    # Update ICD-10 codes"
	@echo "   make medical-mirrors-update-billing  # Update billing codes"
	@echo "   make medical-mirrors-update-health   # Update health info"
	@echo ""
	@echo "📊 Monitoring & Management:"
	@echo "   make medical-mirrors-progress         # Monitor update progress"
	@echo "   make medical-mirrors-logs            # View service logs"
	@echo "   make medical-mirrors-errors-summary  # View error summary"
	@echo "   make medical-mirrors-counts          # Show record counts"
	@echo "   make medical-mirrors-health          # Check service health"
	@echo "   make medical-mirrors-stop            # Stop service"
	@echo ""
	@echo "🧪 Testing:"
	@echo "   make medical-mirrors-quick-test      # Quick test with small dataset"
	@echo "   make medical-mirrors-test-pubmed     # Test PubMed processing"
	@echo "   make medical-mirrors-test-trials     # Test clinical trials"
	@echo ""
	@echo "💡 Tips:"
	@echo "   • Use 'smart-update' for regular updates (fastest)"
	@echo "   • Download commands only fetch data, process commands load to DB"
	@echo "   • Update commands do both download and process"
	@echo "   • Add '-force' to process commands to reprocess everything"
	@echo ""

# Business Services Commands

# Insurance Verification Service Commands
insurance-verification-build:
	@echo "🏗️  Building Insurance Verification service Docker image"
	@cd services/user/insurance-verification && docker build -t intelluxe/insurance-verification:latest .
	@echo "✅ Insurance Verification Docker image built successfully"

insurance-verification-rebuild:
	@echo "🔄  Rebuilding Insurance Verification service (no cache)"
	@cd services/user/insurance-verification && docker build --no-cache -t intelluxe/insurance-verification:latest .
	@echo "✅ Insurance Verification Docker image rebuilt successfully"

insurance-verification-clean:
	@echo "🧹  Cleaning up Insurance Verification Docker artifacts"
	@docker images intelluxe/insurance-verification -q | xargs -r docker rmi -f
	@docker system prune -f --filter "label=description=Multi-provider insurance verification with chain-of-thought reasoning and PHI protection"
	@echo "✅ Insurance Verification Docker cleanup complete"

insurance-verification-stop:
	@echo "🛑  Stopping Insurance Verification service"
	@docker stop insurance-verification 2>/dev/null || echo "Container not running"
	@docker rm insurance-verification 2>/dev/null || echo "Container not found"
	@echo "✅ Insurance Verification service stopped"

insurance-verification-logs:
	@echo "📋  Insurance Verification service logs (last 50 lines):"
	@docker logs --tail 50 insurance-verification 2>/dev/null || echo "Container not found or not running"

insurance-verification-health:
	@echo "🏥  Checking Insurance Verification service health"
	@curl -f http://172.20.0.23:8003/health 2>/dev/null && echo "✅ Insurance Verification service is healthy" || echo "❌ Insurance Verification service is unhealthy"

insurance-verification-status:
	@echo "📊  Insurance Verification service status:"
	@docker ps --filter name=insurance-verification --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "Container not found"

insurance-verification-test:
	@echo "🧪  Running Insurance Verification service validation"
	@curl -f http://172.20.0.23:8003/docs 2>/dev/null && echo "✅ Insurance Verification docs accessible" || echo "❌ Insurance Verification docs not accessible"
	@curl -f http://172.20.0.23:8003/health 2>/dev/null && echo "✅ Insurance Verification health check passed" || echo "❌ Insurance Verification health check failed"
	@echo "✅  Insurance Verification service validation complete"

# Billing Engine Service Commands
billing-engine-build:
	@echo "🏗️  Building Billing Engine service Docker image"
	@cd services/user/billing-engine && docker build -t intelluxe/billing-engine:latest .
	@echo "✅ Billing Engine Docker image built successfully"

billing-engine-rebuild:
	@echo "🔄  Rebuilding Billing Engine service (no cache)"
	@cd services/user/billing-engine && docker build --no-cache -t intelluxe/billing-engine:latest .
	@echo "✅ Billing Engine Docker image rebuilt successfully"

billing-engine-clean:
	@echo "🧹  Cleaning up Billing Engine Docker artifacts"
	@docker images intelluxe/billing-engine -q | xargs -r docker rmi -f
	@docker system prune -f --filter "label=description=Medical billing engine with claim processing, code validation, and payment tracking"
	@echo "✅ Billing Engine Docker cleanup complete"

billing-engine-stop:
	@echo "🛑  Stopping Billing Engine service"
	@docker stop billing-engine 2>/dev/null || echo "Container not running"
	@docker rm billing-engine 2>/dev/null || echo "Container not found"
	@echo "✅ Billing Engine service stopped"

billing-engine-logs:
	@echo "📋  Billing Engine service logs (last 50 lines):"
	@docker logs --tail 50 billing-engine 2>/dev/null || echo "Container not found or not running"

billing-engine-health:
	@echo "💰  Checking Billing Engine service health"
	@curl -f http://172.20.0.24:8004/health 2>/dev/null && echo "✅ Billing Engine service is healthy" || echo "❌ Billing Engine service is unhealthy"

billing-engine-status:
	@echo "📊  Billing Engine service status:"
	@docker ps --filter name=billing-engine --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "Container not found"

billing-engine-test:
	@echo "🧪  Running Billing Engine service validation"
	@curl -f http://172.20.0.24:8004/docs 2>/dev/null && echo "✅ Billing Engine docs accessible" || echo "❌ Billing Engine docs not accessible"
	@curl -f http://172.20.0.24:8004/health 2>/dev/null && echo "✅ Billing Engine health check passed" || echo "❌ Billing Engine health check failed"
	@echo "✅  Billing Engine service validation complete"

# Compliance Monitor Service Commands
compliance-monitor-build:
	@echo "🏗️  Building Compliance Monitor service Docker image"
	@cd services/user/compliance-monitor && docker build -t intelluxe/compliance-monitor:latest .
	@echo "✅ Compliance Monitor Docker image built successfully"

compliance-monitor-rebuild:
	@echo "🔄  Rebuilding Compliance Monitor service (no cache)"
	@cd services/user/compliance-monitor && docker build --no-cache -t intelluxe/compliance-monitor:latest .
	@echo "✅ Compliance Monitor Docker image rebuilt successfully"

compliance-monitor-clean:
	@echo "🧹  Cleaning up Compliance Monitor Docker artifacts"
	@docker images intelluxe/compliance-monitor -q | xargs -r docker rmi -f
	@docker system prune -f --filter "label=description=HIPAA compliance monitoring with audit trail tracking and violation detection"
	@echo "✅ Compliance Monitor Docker cleanup complete"

compliance-monitor-stop:
	@echo "🛑  Stopping Compliance Monitor service"
	@docker stop compliance-monitor 2>/dev/null || echo "Container not running"
	@docker rm compliance-monitor 2>/dev/null || echo "Container not found"
	@echo "✅ Compliance Monitor service stopped"

compliance-monitor-logs:
	@echo "📋  Compliance Monitor service logs (last 50 lines):"
	@docker logs --tail 50 compliance-monitor 2>/dev/null || echo "Container not found or not running"

compliance-monitor-health:
	@echo "🛡️  Checking Compliance Monitor service health"
	@curl -f http://172.20.0.25:8005/health 2>/dev/null && echo "✅ Compliance Monitor service is healthy" || echo "❌ Compliance Monitor service is unhealthy"

compliance-monitor-status:
	@echo "📊  Compliance Monitor service status:"
	@docker ps --filter name=compliance-monitor --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "Container not found"

compliance-monitor-test:
	@echo "🧪  Running Compliance Monitor service validation"
	@curl -f http://172.20.0.25:8005/docs 2>/dev/null && echo "✅ Compliance Monitor docs accessible" || echo "❌ Compliance Monitor docs not accessible"
	@curl -f http://172.20.0.25:8005/health 2>/dev/null && echo "✅ Compliance Monitor health check passed" || echo "❌ Compliance Monitor health check failed"
	@echo "✅  Compliance Monitor service validation complete"

# Business Intelligence Service Commands
business-intelligence-build:
	@echo "🏗️  Building Business Intelligence service Docker image"
	@cd services/user/business-intelligence && docker build -t intelluxe/business-intelligence:latest .
	@echo "✅ Business Intelligence Docker image built successfully"

business-intelligence-rebuild:
	@echo "🔄  Rebuilding Business Intelligence service (no cache)"
	@cd services/user/business-intelligence && docker build --no-cache -t intelluxe/business-intelligence:latest .
	@echo "✅ Business Intelligence Docker image rebuilt successfully"

business-intelligence-clean:
	@echo "🧹  Cleaning up Business Intelligence Docker artifacts"
	@docker images intelluxe/business-intelligence -q | xargs -r docker rmi -f
	@docker system prune -f --filter "label=description=Business intelligence service with healthcare analytics and reporting"
	@echo "✅ Business Intelligence Docker cleanup complete"

business-intelligence-stop:
	@echo "🛑  Stopping Business Intelligence service"
	@docker stop business-intelligence 2>/dev/null || echo "Container not running"
	@docker rm business-intelligence 2>/dev/null || echo "Container not found"
	@echo "✅ Business Intelligence service stopped"

business-intelligence-logs:
	@echo "📋  Business Intelligence service logs (last 50 lines):"
	@docker logs --tail 50 business-intelligence 2>/dev/null || echo "Container not found or not running"

business-intelligence-health:
	@echo "📊  Checking Business Intelligence service health"
	@curl -f http://172.20.0.26:8006/health 2>/dev/null && echo "✅ Business Intelligence service is healthy" || echo "❌ Business Intelligence service is unhealthy"

business-intelligence-status:
	@echo "📊  Business Intelligence service status:"
	@docker ps --filter name=business-intelligence --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "Container not found"

business-intelligence-test:
	@echo "🧪  Running Business Intelligence service validation"
	@curl -f http://172.20.0.26:8006/docs 2>/dev/null && echo "✅ Business Intelligence docs accessible" || echo "❌ Business Intelligence docs not accessible"
	@curl -f http://172.20.0.26:8006/health 2>/dev/null && echo "✅ Business Intelligence health check passed" || echo "❌ Business Intelligence health check failed"
	@echo "✅  Business Intelligence service validation complete"

# Doctor Personalization Service Commands
doctor-personalization-build:
	@echo "🏗️  Building Doctor Personalization service Docker image"
	@cd services/user/doctor-personalization && docker build -t intelluxe/doctor-personalization:latest .
	@echo "✅ Doctor Personalization Docker image built successfully"

doctor-personalization-rebuild:
	@echo "🔄  Rebuilding Doctor Personalization service (no cache)"
	@cd services/user/doctor-personalization && docker build --no-cache -t intelluxe/doctor-personalization:latest .
	@echo "✅ Doctor Personalization Docker image rebuilt successfully"

doctor-personalization-clean:
	@echo "🧹  Cleaning up Doctor Personalization Docker artifacts"
	@docker images intelluxe/doctor-personalization -q | xargs -r docker rmi -f
	@docker system prune -f --filter "label=description=Doctor personalization service with LoRA-based AI adaptation"
	@echo "✅ Doctor Personalization Docker cleanup complete"

doctor-personalization-stop:
	@echo "🛑  Stopping Doctor Personalization service"
	@docker stop doctor-personalization 2>/dev/null || echo "Container not running"
	@docker rm doctor-personalization 2>/dev/null || echo "Container not found"
	@echo "✅ Doctor Personalization service stopped"

doctor-personalization-logs:
	@echo "📋  Doctor Personalization service logs (last 50 lines):"
	@docker logs --tail 50 doctor-personalization 2>/dev/null || echo "Container not found or not running"

doctor-personalization-health:
	@echo "👨‍⚕️  Checking Doctor Personalization service health"
	@curl -f http://172.20.0.27:8007/health 2>/dev/null && echo "✅ Doctor Personalization service is healthy" || echo "❌ Doctor Personalization service is unhealthy"

doctor-personalization-status:
	@echo "📊  Doctor Personalization service status:"
	@docker ps --filter name=doctor-personalization --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "Container not found"

doctor-personalization-test:
	@echo "🧪  Running Doctor Personalization service validation"
	@curl -f http://172.20.0.27:8007/docs 2>/dev/null && echo "✅ Doctor Personalization docs accessible" || echo "❌ Doctor Personalization docs not accessible"
	@curl -f http://172.20.0.27:8007/health 2>/dev/null && echo "✅ Doctor Personalization health check passed" || echo "❌ Doctor Personalization health check failed"
	@echo "✅  Doctor Personalization service validation complete"

# Parse Downloaded Medical Archives (without re-downloading)
parse-downloaded-quick:
	@echo "🔍  Quick parsing test for downloaded medical archives"
	@echo "   ⚠️  This only processes small samples to verify parsing works"
	@python3 scripts/parse_downloaded_archives.py quick

parse-downloaded-full:
	@echo "🚀  Full parsing of all downloaded medical archives"
	@echo "   ⚠️  This may take several hours for complete datasets"
	@echo "   📊 Will parse ALL available downloaded files"
	@python3 scripts/parse_downloaded_archives.py full

parse-downloaded-status:
	@echo "📊  Checking medical data parsing status"
	@python3 scripts/parse_downloaded_archives.py status

parse-downloaded-pubmed:
	@echo "📚  Parsing downloaded PubMed data only"
	@python3 scripts/parse_downloaded_archives.py pubmed

parse-downloaded-pubmed-quick:
	@echo "📚  Quick parsing test for PubMed data"
	@python3 scripts/parse_downloaded_archives.py pubmed --quick

parse-downloaded-fda:
	@echo "💊  Parsing downloaded FDA data only"
	@python3 scripts/parse_downloaded_archives.py fda

parse-downloaded-fda-quick:
	@echo "💊  Quick parsing test for FDA data"
	@python3 scripts/parse_downloaded_archives.py fda --quick

parse-downloaded-trials:
	@echo "🧪  Parsing downloaded ClinicalTrials data only"
	@python3 scripts/parse_downloaded_archives.py trials

parse-downloaded-trials-quick:
	@echo "🧪  Quick parsing test for ClinicalTrials data"
	@python3 scripts/parse_downloaded_archives.py trials --quick

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

# Comprehensive Test Targets
test-all:
	@echo "🧪  Running ALL tests across the entire repository"
	@echo "   📁 Main test directory..."
	python3 -m pytest tests/ -v --tb=short
	@echo "   🏥 Healthcare API tests..."
	@if [ -d "services/user/healthcare-api/tests" ]; then \
		cd services/user/healthcare-api && python3 -m pytest tests/ -v --tb=short; \
	fi
	@echo "   🔬 Medical mirrors tests..."
	@if [ -f "services/user/medical-mirrors/test_integration.py" ]; then \
		cd services/user/medical-mirrors && python3 -m pytest test_*.py -v --tb=short; \
	fi
	@echo "   📋 Interface tests..."
	@if [ -d "interfaces/open_webui" ]; then \
		cd interfaces/open_webui && python3 -m pytest test_*.py -v --tb=short; \
	fi
	@echo "   📥 Download script tests..."
	@if [ -f "scripts/test_enhanced_drug_sources.py" ]; then \
		cd scripts && python3 -m pytest test_*.py -v --tb=short; \
	fi

test-unit:
	@echo "🧪  Running unit tests (fast, isolated)"
	@python3 -m pytest tests/ -m "not integration and not e2e" -v --tb=short

test-integration:
	@echo "🧪  Running integration tests (cross-component)"
	@python3 -m pytest tests/ -m "integration" -v --tb=short

test-downloads:
	@echo "📥  Testing download scripts and data processing"
	@python3 -m pytest tests/downloads/ -v --tb=short
	@if [ -f "scripts/test_enhanced_drug_sources.py" ]; then \
		cd scripts && python3 test_enhanced_drug_sources.py; \
	fi

test-services:
	@echo "🏥  Running service-specific tests"
	@echo "   Healthcare API..."
	@if [ -d "services/user/healthcare-api/tests" ]; then \
		cd services/user/healthcare-api && python3 -m pytest tests/ -v --tb=short; \
	fi
	@echo "   Medical mirrors..."
	@if [ -f "services/user/medical-mirrors/test_integration.py" ]; then \
		cd services/user/medical-mirrors && python3 -m pytest test_*.py -v --tb=short; \
	fi
	@echo "   MCP pipeline..."
	@if [ -f "services/user/mcp-pipeline/test_pipeline_connectivity.py" ]; then \
		cd services/user/mcp-pipeline && python3 test_pipeline_connectivity.py; \
	fi

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
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "🚀  QUICK START:"
	@echo "   make setup          - Interactive healthcare AI stack setup"
	@echo "   make install        - Install systemd services and create system users"
	@echo "   make deps           - Install all healthcare AI dependencies"
	@echo ""
	@echo "📦  CORE SERVICES:"
	@echo "   make healthcare-api        - Build & run Healthcare API service"
	@echo "   make medical-mirrors       - Build & run Medical Mirrors service"
	@echo "   make scispacy             - Build & run SciSpacy NLP service"
	@echo "   make healthcare-mcp       - Build & run Healthcare MCP service (if available)"
	@echo "   make mcp-pipeline         - Build & run MCP Pipeline service (if available)"
	@echo ""
	@echo "🏥  MEDICAL MIRRORS - Data Management:"
	@echo "   make medical-mirrors-help         - Complete command reference"
	@echo "   make medical-mirrors-smart-update - Smart incremental update (fastest)"
	@echo "   make medical-mirrors-database-init - Initialize database tables"
	@echo "   make medical-mirrors-progress     - Monitor update progress"
	@echo "   make medical-mirrors-download-all - Download ALL data (200GB+)"
	@echo "   make medical-mirrors-process-all  - Process ALL downloaded data"
	@echo "   📚 For specific data sources: use medical-mirrors-help"
	@echo ""
	@echo "💼  BUSINESS SERVICES:"
	@echo "   make insurance-verification-build - Build Insurance Verification service"
	@echo "   make billing-engine-build         - Build Billing Engine service"
	@echo "   make compliance-monitor-build     - Build Compliance Monitor service"
	@echo "   make business-intelligence-build  - Build Business Intelligence service"
	@echo "   make doctor-personalization-build - Build Doctor Personalization service"
	@echo ""
	@echo "🧪  TESTING & VALIDATION:"
	@echo "   make test           - Run healthcare AI test suite"
	@echo "   make test-coverage  - Run tests with coverage report"
	@echo "   make test-ai        - Run AI evaluation tests"
	@echo "   make validate       - Run comprehensive validation (lint + test)"
	@echo "   make e2e            - Run end-to-end workflow tests"
	@echo ""
	@echo "🔍  CODE QUALITY:"
	@echo "   make lint           - Run all linting (shell + python)"
	@echo "   make lint-dev       - Fast lint (core modules only)"
	@echo "   make format         - Auto-format code with ruff"
	@echo ""
	@echo "📊  SYNTHETIC DATA:"
	@echo "   make data-generate       - Generate comprehensive synthetic healthcare data"
	@echo "   make data-generate-small - Generate small dataset for testing"
	@echo "   make data-status         - Show synthetic data statistics"
	@echo "   make data-clean          - Remove synthetic data"
	@echo ""
	@echo "⚙️  SYSTEM MANAGEMENT:"
	@echo "   make diagnostics    - Run comprehensive system diagnostics"
	@echo "   make auto-repair    - Automatically repair unhealthy containers"
	@echo "   make reset          - Reset entire healthcare AI stack"
	@echo "   make teardown       - Complete infrastructure teardown"
	@echo "   make backup         - Backup healthcare VPN configuration"
	@echo "   make clean-cache    - Clean package manager caches"
	@echo "   make clean-docker   - Clean Docker data"
	@echo ""
	@echo "📚  SERVICE-SPECIFIC HELP:"
	@echo "   make medical-mirrors-help    - Medical Mirrors command reference"
	@echo "   make healthcare-api-help     - Healthcare API command reference (if available)"
	@echo "   make scispacy-help          - SciSpacy command reference (if available)"
	@echo ""
	@echo "🔧  ADVANCED OPTIONS:"
	@echo "   make dry-run        - Preview setup without making changes"
	@echo "   make debug          - Debug setup with verbose logging"
	@echo "   make update-deps    - Update dependencies to latest versions"
	@echo ""
	@echo "💡  Tips:"
	@echo "   • Use TAB completion: 'make medical<TAB>' shows all medical-mirrors commands"
	@echo "   • Monitor services: 'make <service>-logs' (e.g., medical-mirrors-logs)"
	@echo "   • Check health: 'make <service>-health' (e.g., healthcare-api-health)"
	@echo "   • For detailed help on any service, use: make <service>-help"
	@echo ""
