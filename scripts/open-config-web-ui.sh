#!/usr/bin/env bash
set -euo pipefail
# open-config-web-ui.sh - Launch the configuration web interface in the default browser
# Author: Justin Michael Sue (Galdaer)
# Repo: https://github.com/Intelluxe-AI/intelluxe-core
#
# Copyright (c) 2025 Justin Michael Sue
#
# Dual License Notice:
# This software is available under two licensing options:
#
# 1. AGPL v3.0 License (Open Source)
#    - Free for personal, educational, and open-source use
#    - Requires derivative works to also be open source
#    - See LICENSE-AGPL file for full terms
#
# 2. Commercial License
#    - For proprietary/commercial use without AGPL restrictions
#    - Contact: licensing@intelluxeai.com for commercial licensing terms
#    - Allows embedding in closed-source products
#
# Choose the license that best fits your use case.
#
# TRADEMARK NOTICE: "Intelluxe" and related branding may be trademark protected.
# Commercial use of project branding requires separate permission.
#_______________________________________________________________________________

# Determine path to configuration file. CFG_ROOT can override the default
CFG="${CFG_ROOT:-/opt/intelluxe/stack}/.bootstrap.conf"

# Extract configured port from the bootstrap configuration
PORT=$(grep -m1 -E "^CONFIG_WEB_UI_PORT=" "$CFG" 2>/dev/null | cut -d= -f2)

# Fall back to default port 9123 if not set
PORT="${PORT:-9123}"

# Open the interface in the default browser. Use xdg-open on Linux,
# fall back to the macOS 'open' command if available. Print the URL if
# no opener is found.
URL="http://localhost:${PORT}"
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL"
elif command -v open >/dev/null 2>&1; then
    open "$URL"
else
    echo "Open $URL in your browser" >&2
fi
