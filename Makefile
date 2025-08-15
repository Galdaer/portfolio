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
	   mcp \
	   mcp-build \
	   mcp-rebuild \
	   mcp-clean \
	   mcp-pipeline \
	   mcp-pipeline-build \
	   mcp-pipeline-rebuild \
	   mcp-pipeline-clean \
	   mcp-pipeline-run \
	   mcp-pipeline-stop \
	   mcp-pipeline-restart \
	   mcp-pipeline-logs \
	   mcp-pipeline-health \
	   mcp-pipeline-status \
	mcp-pipeline-test \
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
	   medical-mirrors-progress \
	   medical-mirrors-quick-test \
	   medical-mirrors-validate-downloads \
	   medical-mirrors-debug-ncbi \
	   medical-mirrors-clean-data \
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

# Single-command restarts for interactive services (14 entries)
grafana:
	$(call BOOTSTRAP_RESTART,grafana,1)

healthcare-api:
	$(call BOOTSTRAP_RESTART,healthcare-api,2)

healthcare-mcp:
	$(call BOOTSTRAP_RESTART,healthcare-mcp,3)

mcp-pipeline:
	$(call BOOTSTRAP_RESTART,mcp-pipeline,4)

medical-mirrors:
	$(call BOOTSTRAP_RESTART,medical-mirrors,5)

n8n:
	$(call BOOTSTRAP_RESTART,n8n,6)

ollama:
	$(call BOOTSTRAP_RESTART,ollama,7)

ollama-webui:
	$(call BOOTSTRAP_RESTART,ollama-webui,8)

postgresql:
	$(call BOOTSTRAP_RESTART,postgresql,9)

redis:
	$(call BOOTSTRAP_RESTART,redis,10)

scispacy:
	$(call BOOTSTRAP_RESTART,scispacy,11)

traefik:
	$(call BOOTSTRAP_RESTART,traefik,12)

wireguard:
	$(call BOOTSTRAP_RESTART,wireguard,13)

wyoming-whisper:
	$(call BOOTSTRAP_RESTART,wyoming-whisper,14)


mcp: healthcare-mcp

mcp-build:
	@echo "🏗️  Building Healthcare MCP server Docker image"
	@cd services/user/healthcare-mcp && docker build -t intelluxe/healthcare-mcp:latest .
	@echo "✅ Healthcare MCP Docker image built successfully"

mcp-rebuild:
	@echo "🔄  Rebuilding Healthcare MCP server (no cache)"
	@cd services/user/healthcare-mcp && docker build --no-cache -t intelluxe/healthcare-mcp:latest .
	@echo "✅ Healthcare MCP Docker image rebuilt successfully"

mcp-clean:
	@echo "🧹  Cleaning up Healthcare MCP Docker artifacts"
	@docker images intelluxe/healthcare-mcp -q | xargs -r docker rmi -f
	@docker system prune -f --filter "label=maintainer=Intelluxe AI Healthcare Team"
	@echo "✅ Healthcare MCP Docker cleanup complete"

# MCP Pipeline Service Commands (Open WebUI Integration)
mcp-pipeline-build:
	@echo "🏗️  Building MCP Pipeline service Docker image"
	@cd services/user/mcp-pipeline && docker build -t intelluxe/mcp-pipeline:latest .
	@echo "✅ MCP Pipeline Docker image built successfully"

mcp-pipeline-rebuild:
	@echo "🔄  Rebuilding MCP Pipeline service (no cache)"
	@cd services/user/mcp-pipeline && docker build --no-cache -t intelluxe/mcp-pipeline:latest .
	@echo "✅ MCP Pipeline Docker image rebuilt successfully"

mcp-pipeline-clean:
	@echo "🧹  Cleaning up MCP Pipeline Docker artifacts"
	@docker images intelluxe/mcp-pipeline -q | xargs -r docker rmi -f
	@docker system prune -f --filter "label=service=mcp-pipeline"
	@echo "✅ MCP Pipeline Docker cleanup complete"

# MCP Pipeline test targets
mcp-pipeline-stdio-test: mcp-pipeline
	@echo "🧪  MCP Pipeline stdio-only test (DISABLE_HTTP_FALLBACK=1)"
	@docker run --rm --network intelluxe-net \
	  -e PIPELINES_PORT=9099 \
	  -e MCP_CONFIG_PATH=/app/data/mcp_config.json \
	  -e HEALTHCARE_MCP_CONTAINER=healthcare-mcp-stdio \
	  -e DISABLE_HTTP_FALLBACK=1 \
	  intelluxe/mcp-pipeline:latest bash -lc 'set -e; ./start_pipeline.sh & PID=$$!; for i in $$(seq 1 25); do sleep 1; curl -sf http://localhost:9099/health >/dev/null 2>&1 && break || true; done; echo "Health OK"; curl -s http://localhost:9099/tools | jq ".data | length"; kill $$PID || true; wait $$PID 2>/dev/null || true'
	@echo "✅  Stdio test complete"

mcp-pipeline-full-test: mcp-pipeline
	@echo "🧪  MCP Pipeline full test (stdio + HTTP fallback)"
	@docker run --rm --network intelluxe-net \
	  -e PIPELINES_PORT=9099 \
	  -e MCP_CONFIG_PATH=/app/data/mcp_config.json \
	  -e HEALTHCARE_MCP_CONTAINER=healthcare-mcp-stdio \
	  intelluxe/mcp-pipeline:latest bash -lc 'set -e; ./start_pipeline.sh & PID=$$!; for i in $$(seq 1 25); do sleep 1; curl -sf http://localhost:9099/health >/dev/null 2>&1 && break || true; done; echo "Health OK"; curl -s http://localhost:9099/tools | jq ".data | {count: length, sample: (.[0:3]|map(.id))}"; kill $$PID || true; wait $$PID 2>/dev/null || true'
	@echo "✅  Full test complete"

mcp-pipeline-stop:
	@echo "🛑  Stopping MCP Pipeline service"
	@docker stop mcp-pipeline 2>/dev/null || echo "Container not running"
	@docker rm mcp-pipeline 2>/dev/null || echo "Container not found"
	@echo "✅ MCP Pipeline service stopped"

mcp-pipeline-logs:
	@echo "📋  MCP Pipeline service logs (last 50 lines):"
	@docker logs --tail 50 mcp-pipeline 2>/dev/null || echo "Container not found or not running"

mcp-pipeline-health:
	@echo "🏥  Checking MCP Pipeline service health"
	@curl -f http://172.20.0.15:9099/health 2>/dev/null && echo "✅ MCP Pipeline service is healthy" || echo "❌ MCP Pipeline service is unhealthy"

mcp-pipeline-status:
	@echo "📊  MCP Pipeline service status:"
	@docker ps --filter name=mcp-pipeline --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "Container not found"

mcp-pipeline-test:
	@echo "🧪  Running MCP Pipeline validation script"
	@bash scripts/test_mcp_pipeline.sh
	@echo "✅  MCP Pipeline validation complete"

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
	@echo "🔄  Updating all Medical Mirrors databases"
	@echo "   ⚠️  WARNING: This process will take HOURS and may hit rate limits!"
	@echo "   📊 Monitor progress: make medical-mirrors-progress"
	@echo "   🛑 To stop: make medical-mirrors-stop"
	@echo ""
	@echo "   🔍 Testing service status first..."
	@if curl -f -m 5 http://localhost:8081/status 2>/dev/null | jq '.service' 2>/dev/null; then \
		echo "   ✅ Service responding"; \
		echo "   🚀 Starting async update process..."; \
		curl -X POST http://localhost:8081/update/pubmed -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   📚 PubMed update started in background"; \
		sleep 2; \
		curl -X POST http://localhost:8081/update/trials -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   🧪 Trials update started in background"; \
		sleep 2; \
		curl -X POST http://localhost:8081/update/fda -H "Content-Type: application/json" --max-time 10 >/dev/null 2>&1 & \
		echo "   💊 FDA update started in background"; \
		echo "   ✅ All update requests sent asynchronously"; \
		echo "   📊 Monitor progress: make medical-mirrors-progress"; \
		echo "   🚨 Check errors: make medical-mirrors-errors-summary"; \
	else \
		echo "   ❌ Service not responding - start with: make medical-mirrors-run"; \
		exit 1; \
	fi
	@echo "✅ Update processes started - use 'make medical-mirrors-progress' to monitor" 

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

medical-mirrors-quick-test:
	@echo "🚀  Quick test update (testing all 3 data sources with SMALL samples)"
	@echo "   ⚠️  This will download minimal subsets for fast testing only"
	@echo "   📊 Sample sizes: PubMed=3 files, Trials=100 studies, FDA=1000 drugs"
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
	@echo "   make clean-docker   - Clean Docker data (images, containers, volumes)"
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
	@echo "   make mcp			 - Start Healthcare MCP server"
	@echo "   make mcp-build           - Build Healthcare MCP server Docker image"
	@echo "   make mcp-rebuild   - Rebuild MCP server (no cache)"
	@echo "   make mcp-clean     - Clean MCP Docker artifacts"
	@echo ""
	@echo "🔌  MCP PIPELINE (Open WebUI Integration):"
	@echo "   make mcp-pipeline         - Start MCP Pipeline service"
	@echo "   make mcp-pipeline-build       - Build MCP Pipeline service Docker image"
	@echo "   make mcp-pipeline-rebuild - Rebuild MCP Pipeline (no cache)"
	@echo "   make mcp-pipeline-logs    - View MCP Pipeline logs"
	@echo "   make mcp-pipeline-health  - Check MCP Pipeline health"
	@echo "   make mcp-pipeline-status  - Show MCP Pipeline status"
	@echo "   make mcp-pipeline-clean   - Clean MCP Pipeline Docker artifacts"
	@echo "   make mcp-pipeline-stdio-test  - Run stdio-only MCP pipeline tool discovery test"
	@echo "   make mcp-pipeline-full-test   - Run stdio + HTTP fallback pipeline test"
	@echo ""
	@echo "🧬  SCISPACY NLP SERVICE:"
	@echo "   make scispacy         - Start SciSpacy NLP service"
	@echo "   make scispacy-build   - Build SciSpacy Docker image"
	@echo "   make scispacy-rebuild - Rebuild SciSpacy (no cache)"
	@echo "   make scispacy-logs    - View SciSpacy logs"
	@echo "   make scispacy-health  - Check SciSpacy health"
	@echo "   make scispacy-status  - Show SciSpacy status"
	@echo "   make scispacy-test    - Test SciSpacy entity analysis"
	@echo "   make scispacy-clean   - Clean SciSpacy Docker artifacts"
	@echo ""
	@echo "🏥  MEDICAL MIRRORS SERVICE:"
	@echo "   make medical-mirrors         - Start Medical Mirrors service"
	@echo "   make medical-mirrors-build   - Build Medical Mirrors Docker image"
	@echo "   make medical-mirrors-rebuild - Rebuild Medical Mirrors (no cache)"
	@echo "   make medical-mirrors-logs    - View Medical Mirrors logs"
	@echo "   make medical-mirrors-errors  - View Medical Mirrors ERRORS ONLY"
	@echo "   make medical-mirrors-errors-summary - Concise error summary with counts"
	@echo "   make medical-mirrors-stop    - Stop Medical Mirrors service"
	@echo "   make medical-mirrors-health  - Check Medical Mirrors health"
	@echo "   make medical-mirrors-clean   - Clean Medical Mirrors Docker artifacts"
	@echo ""
	@echo "�  DATA UPDATES (WARNING: VERY TIME CONSUMING!):"
	@echo "   make medical-mirrors-quick-test     - Quick test update (small dataset)"
	@echo "   make medical-mirrors-update         - Update ALL databases (6-12+ hours!)"
	@echo "   make medical-mirrors-update-pubmed  - Update PubMed only (6-12+ hours!)"
	@echo "   make medical-mirrors-update-trials  - Update ClinicalTrials (2-4+ hours!)"
	@echo "   make medical-mirrors-update-fda     - Update FDA only (1-3+ hours!)"
	@echo "   make medical-mirrors-progress       - Monitor update progress (real-time)"
	@echo ""
	@echo "⚙️   SYSTEM MANAGEMENT:"
	@echo "   make diagnostics   - Run comprehensive system diagnostics"
	@echo "   make auto-repair   - Automatically repair unhealthy containers"
	@echo "   make reset         - Reset entire healthcare AI stack"
	@echo "   make teardown      - Complete infrastructure teardown"
	@echo "   make backup        - Backup healthcare VPN configuration"
