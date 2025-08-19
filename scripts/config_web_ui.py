#!/usr/bin/env python3
# config_web_ui.py - Simple Flask UI for editing Intelluxe AI configuration
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
# _______________________________________________________________________________
"""Simple Flask UI for editing Intelluxe AI healthcare configuration."""

import glob
import html
import os
import re
import shutil
import subprocess
import time
import warnings
from typing import Any

from flask import (
    Flask,
    redirect,
    render_template_string,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.wrappers import Response

# Compiled regex patterns for performance
ALL_CONTAINERS_PATTERN = re.compile(r"^ALL_CONTAINERS=\(([^)]*)\)")


def build_service_prefix_map() -> dict[str, str]:
    """Return mapping of config prefixes to service names.

    The returned dictionary is ordered with longer prefixes first to
    avoid substring collisions when matching environment keys.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prefix_mapping: dict[str, tuple[str, str]] = {}
    for service_dir in ("core", "user"):
        conf_dir = os.path.join(root, "services", service_dir)
        if not os.path.isdir(conf_dir):
            continue
        for path in sorted(glob.glob(os.path.join(conf_dir, "*.conf"))):
            name = os.path.splitext(os.path.basename(path))[0]
            key = name.upper()
            if key in prefix_mapping:
                prev_name, prev_dir = prefix_mapping[key]
                warnings.warn(
                    f"Duplicate service config '{name}' found in '{service_dir}' directory; "
                    f"already saw '{prev_name}' in '{prev_dir}' directory; ignoring",
                    stacklevel=2,
                )
                continue
            prefix_mapping[key] = (name, service_dir)
    # Ensure longer prefixes appear first to avoid substring collisions
    service_map = {k: v[0] for k, v in prefix_mapping.items()}
    return dict(sorted(service_map.items(), key=lambda kv: len(kv[0]), reverse=True))


SERVICE_PREFIX_MAP = build_service_prefix_map()

# Additional configuration fields to expose in the web UI.
EXTRA_FIELDS = [
    "VPN_SUBNET",
    "VPN_SUBNET_BASE",
    "FIREWALL_RESTRICT_MODE",
    "RESTRICTED_SERVICES",
    "CONFIG_WEB_UI_PORT",
]

CFG_ROOT = os.environ.get("CFG_ROOT", "/opt/intelluxe/stack")
LOGS_DIR = os.path.join(CFG_ROOT, "logs")
CONFIG_FILE = os.path.join(CFG_ROOT, ".bootstrap.conf")
PORT = int(os.environ.get("CONFIG_WEB_UI_PORT", 9123))
BOOTSTRAP_PATH = os.environ.get("BOOTSTRAP_PATH")
if not BOOTSTRAP_PATH:
    BOOTSTRAP_PATH = shutil.which("bootstrap.sh") or "/usr/local/bin/bootstrap.sh"
TEARDOWN_PATH = os.environ.get("TEARDOWN_PATH")
if not TEARDOWN_PATH:
    TEARDOWN_PATH = shutil.which("teardown.sh") or "/usr/local/bin/teardown.sh"

app = Flask(__name__)

FORM_TEMPLATE = """
<!doctype html>
<title>Intelluxe AI Configuration</title>
<h1>Intelluxe Healthcare AI Configuration Editor</h1>
<form method="post">
<table>
{% for key, value in config.items() %}
  <tr><td>{{ key }}</td><td>
    {% if key == 'SELECTED_CONTAINERS' %}
      <select name="SELECTED_CONTAINERS" multiple size="{{ all_containers|length }}">
      {% for c in all_containers %}
        <option value="{{ c }}" {% if c in value %}selected{% endif %}>{{ c }}</option>
      {% endfor %}
      </select>
    {% else %}
      <input name="{{ key }}" value="{{ value }}">
    {% endif %}
  </td></tr>
{% endfor %}
</table>
<input type="submit" value="Save">
</form>
<h2>Healthcare AI System Maintenance</h2>
<form action="{{ url_for('bootstrap') }}" method="post" onsubmit="return confirm('Run full Intelluxe bootstrap?');">
  <button type="submit">Run Bootstrap</button>
</form>
<form action="{{ url_for('self_update') }}" method="post" onsubmit="return confirm('Update bootstrap script?');">
  <button type="submit">Self Update Script</button>
</form>
<form action="{{ url_for('reset_wg_keys') }}" method="post" onsubmit="return confirm('Reset WireGuard server keys?');">
  <button type="submit">Reset WireGuard Keys</button>
</form>
<form action="{{ url_for('diagnostics') }}" method="post">
  <button type="submit">Run AI System Diagnostics</button>
</form>
<form action="{{ url_for('auto_repair') }}" method="post">
  <button type="submit">Run Auto Repair</button>
</form>
<form action="{{ url_for('reset_system_route') }}" method="post" onsubmit="return confirm('Reset entire Intelluxe stack?');">
  <button type="submit">Run System Reset</button>
</form>
<form action="{{ url_for('systemd_summary_route') }}" method="get">
  <button type="submit">Systemd Summary</button>
</form>
<form action="{{ url_for('teardown_route') }}" method="post" onsubmit="return confirm('Teardown entire Intelluxe stack?');">
  <button type="submit">Run Teardown</button>
</form>

<h2>Healthcare AI Service Control</h2>
<form id="startForm" action="{{ url_for('start_service_route') }}" method="post">
  <select name="service">
  {% for svc in all_containers %}
    <option value="{{ svc }}">{{ svc }}</option>
  {% endfor %}
  </select>
  <button type="submit">Start Service</button>
</form>
<form id="restartForm" action="{{ url_for('restart_service_route') }}" method="post">
  <select name="service">
  {% for svc in all_containers %}
    <option value="{{ svc }}">{{ svc }}</option>
  {% endfor %}
  </select>
  <button type="submit">Restart Service</button>
</form>
<form id="stopForm" action="{{ url_for('stop_service_route') }}" method="post">
  <select name="service">
  {% for svc in all_containers %}
    <option value="{{ svc }}">{{ svc }}</option>
  {% endfor %}
  </select>
  <button type="submit">Stop Service</button>
</form>
<form id="removeForm" action="{{ url_for('remove_service_route') }}" method="post">
  <select name="service">
  {% for svc in all_containers %}
    <option value="{{ svc }}">{{ svc }}</option>
  {% endfor %}
  </select>
  <button type="submit">Remove Service</button>
</form>
<h2>Healthcare AI Service Status</h2>
<table>
  {% for svc in all_containers %}
    <tr>
      <td><a href="{{ url_for('logs_index', name=svc) }}">{{ svc }}</a></td>
      <td>{{ container_status.get(svc, 'unknown') }}</td>
      {% if svc == 'ollama' %}
        <td>🧠 AI Inference</td>
      {% elif svc == 'healthcare-mcp' %}
        <td>🏥 Medical Tools</td>
      {% elif svc == 'postgres' %}
        <td>💾 Patient Database</td>
      {% elif svc == 'redis' %}
        <td>⚡ Session Cache</td>
      {% elif svc == 'n8n' %}
        <td>🔄 Workflow Automation</td>
      {% else %}
        <td>📊 System Service</td>
      {% endif %}
    </tr>
  {% endfor %}
</table>
<h2>Quick Healthcare AI Links</h2>
<p><a href="http://172.20.0.10:11434" target="_blank">🧠 Ollama API (Local LLM)</a></p>
<p><a href="http://localhost:3000" target="_blank">🏥 Healthcare-MCP Dashboard</a></p>
<p><a href="http://localhost:5678" target="_blank">🔄 n8n Workflow Editor</a></p>
<p><a href="http://localhost:{{ grafana_port }}" target="_blank">📊 Grafana Monitoring</a></p>
<h2>Add Healthcare AI Service</h2>
<form id="addServiceForm" action="{{ url_for('add_service_route') }}" method="post">
  <input name="service" placeholder="Service name">
  <input name="image" placeholder="Docker image">
  <input name="port" placeholder="Default port">
  <input name="description" placeholder="Description">
  <button type="submit">Add Service</button>
</form>
<p><a href="{{ url_for('logs_index') }}">View Logs</a></p>
<p><a href="http://localhost:{{ grafana_port }}">Grafana Dashboard</a></p>
<script>
const original = {{ config | tojson }};
const serviceMap = {{ service_map | tojson }};

function getService(key) {
  for (const prefix in serviceMap) {
    if (key.startsWith(prefix)) return serviceMap[prefix];
  }
  return null;
}

document.querySelector('form').addEventListener('submit', function(e) {
  const changed = new Set();
  for (const key in original) {
    const el = document.querySelector(`[name="${key}"]`);
    if (!el) continue;
    if (original[key] !== el.value) {
      const svc = getService(key);
      if (svc) changed.add(svc);
    }
  }
  if (changed.size) {
    if (!confirm('Saving will restart: ' + Array.from(changed).join(', ') + '. Continue?')) {
      e.preventDefault();
    }
  }
});
['startForm', 'restartForm', 'stopForm', 'removeForm'].forEach(id => {
  const form = document.getElementById(id);
  if (!form) return;
  form.addEventListener('submit', function(e) {
    const svc = this.service.value;
    const action = id.replace('Form', '');
    const msg = action.charAt(0).toUpperCase() + action.slice(1) + ' ' + svc + '?';
    if (!confirm(msg)) {
      e.preventDefault();
    }
  });
});
const addForm = document.getElementById('addServiceForm');
if (addForm) {
  addForm.addEventListener('submit', function(event) {
    const image = event.currentTarget.querySelector('[name="image"]').value;
    if (!confirm(`Install service using image ${image}?`)) {
      event.preventDefault();
    }
  });
}
</script>
"""


def parse_value(val: str) -> str | list[str]:
    """Parse a configuration value, returning list for bash array syntax."""
    val = val.strip().strip('"')
    if val.startswith("(") and val.endswith(")"):
        return val[1:-1].split()
    return val


def get_all_containers() -> list[str]:
    """Extract ALL_CONTAINERS array from the bootstrap script."""
    try:
        if BOOTSTRAP_PATH is None:
            return []
        with open(BOOTSTRAP_PATH) as f:
            for line in f:
                m = ALL_CONTAINERS_PATTERN.search(line.strip())
                if m:
                    return m.group(1).split()
    except FileNotFoundError:
        pass
    return []


def load_config() -> dict[str, Any]:
    data = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                data[k.strip()] = parse_value(v)
    return data


def get_grafana_default_port() -> str:
    """Return default Grafana port from the service file."""
    conf = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "services",
        "core",
        "grafana.conf",
    )
    try:
        with open(conf) as f:
            for line in f:
                if line.startswith("port="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return "3001"


def get_grafana_port(config: dict[str, Any]) -> str:
    """Derive Grafana port from config or default service file."""
    return str(config.get("CONTAINER_PORTS[grafana]", get_grafana_default_port()))


def save_config(new_data: dict[str, Any]) -> None:
    config = load_config()
    config.update(new_data)
    with open(CONFIG_FILE, "w") as f:
        for k, v in config.items():
            if isinstance(v, list):
                f.write(f"{k}=(" + " ".join(v) + ")\n")
            else:
                f.write(f'{k}="{v}"\n')
    uid = int(os.environ.get("CFG_UID", 1000))
    gid = int(os.environ.get("CFG_GID", 1000))
    os.chown(CONFIG_FILE, uid, gid)


def key_to_service(key: str) -> str | None:
    """Return service name for a given configuration key.

    Supports ``CONTAINER_PORTS[service]`` style keys in addition to the
    traditional ``SERVICE_PREFIX_PORT`` format.
    """
    m = re.match(r"^CONTAINER_PORTS\[(.+?)\]$", key)
    if m:
        return m.group(1)
    for prefix, svc in SERVICE_PREFIX_MAP.items():
        if key.startswith(prefix):
            return svc
    return None


def changed_services(old: dict[str, Any], new: dict[str, Any]) -> set[str]:
    """Return a set of services whose config values changed."""
    services = set()
    for k, val in new.items():
        if old.get(k) != val:
            svc = key_to_service(k)
            if svc:
                services.add(svc)
    return services


def run_bootstrap(
    args: list[str] | None = None, env: dict[str, str] | None = None, suppress: bool = True,
) -> subprocess.Popen[bytes]:
    """Run ``bootstrap.sh`` with optional arguments.

    Parameters
    ----------
    args : list[str] | None
        Additional command line arguments for the bootstrap script.
    env : dict[str, str] | None
        Environment variables to use when invoking the script. ``None``
        results in a copy of the current ``os.environ``.
    suppress : bool
        If ``True`` stderr and stdout of the process are redirected to
        ``subprocess.DEVNULL``.

    Returns
    -------
    subprocess.Popen
        The ``Popen`` object for the launched process.
    """
    if BOOTSTRAP_PATH is None:
        raise RuntimeError("BOOTSTRAP_PATH is not set")

    if env is None:
        env = os.environ.copy()
    cmd = [BOOTSTRAP_PATH, "--non-interactive"]
    if args:
        cmd.extend(args)

    if suppress:
        return subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return subprocess.Popen(cmd, env=env)


def get_container_statuses() -> dict[str, str]:
    """Return mapping of container name to Docker status."""
    try:
        output = subprocess.check_output(
            ["docker", "ps", "-a", "--format", "{{.Names}} {{.Status}}"],
            text=True,
        )
    except Exception:
        return {}
    statuses = {}
    for line in output.strip().splitlines():
        parts = line.split(maxsplit=1)
        if not parts:
            continue
        name = parts[0]
        status = parts[1] if len(parts) > 1 else ""
        statuses[name] = status
    return statuses


@app.route("/", methods=["GET", "POST"])
def index() -> str | Response:
    config = load_config()
    # Ensure configurable web UI port is always available
    if "CONFIG_WEB_UI_PORT" not in config:
        config["CONFIG_WEB_UI_PORT"] = os.environ.get("CONFIG_WEB_UI_PORT", "9123")
    grafana_port = get_grafana_port(config)
    editable = {
        k: v
        for k, v in config.items()
        if k.endswith(("_PORT", "_ROOT", "_DIR")) or k == "SELECTED_CONTAINERS" or k in EXTRA_FIELDS
    }
    all_containers = get_all_containers()
    if request.method == "POST":
        updates = {}
        for k, v in editable.items():
            if k == "SELECTED_CONTAINERS":
                updates[k] = request.form.getlist(k) or []
            else:
                updates[k] = request.form.get(k, v)
        selected_changed = editable.get("SELECTED_CONTAINERS") != updates.get("SELECTED_CONTAINERS")
        services = changed_services(editable, updates)
        save_config(updates)
        for svc in services:
            env = os.environ.copy()
            env.update({"ACTION_FLAG": "--restart", "ACTION_CONTAINER": svc})
            run_bootstrap(env=env)
        if selected_changed:
            run_bootstrap()
        return redirect(url_for("index"))
    return render_template_string(
        FORM_TEMPLATE,
        config=editable,
        service_map=SERVICE_PREFIX_MAP,
        all_containers=all_containers,
        grafana_port=grafana_port,
        container_status=get_container_statuses(),
    )


@app.route("/bootstrap", methods=["POST"])
def bootstrap() -> Response:
    """Run full bootstrap without ACTION_FLAG."""
    env = os.environ.copy()
    run_bootstrap(env=env)
    return redirect(url_for("index"))


@app.route("/reset-wg-keys", methods=["POST"])
def reset_wg_keys() -> Response:
    env = os.environ.copy()
    run_bootstrap(["--reset-wg-keys"], env=env)
    return redirect(url_for("index"))


@app.route("/self-update", methods=["POST"])
def self_update() -> Response:
    env = os.environ.copy()
    run_bootstrap(["--self-update"], env=env)
    return redirect(url_for("index"))


@app.route("/diagnostics", methods=["POST"])
def diagnostics() -> Response:
    env = os.environ.copy()
    subprocess.Popen(
        ["/usr/local/bin/diagnostics.sh", "--non-interactive"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    return redirect(url_for("index"))


@app.route("/auto-repair", methods=["POST"])
def auto_repair() -> Response:
    env = os.environ.copy()
    subprocess.Popen(
        ["/usr/local/bin/auto-repair.sh", "--non-interactive"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    return redirect(url_for("index"))


@app.route("/reset-system", methods=["POST"])
def reset_system_route() -> Response:
    env = os.environ.copy()
    subprocess.Popen(
        ["/usr/local/bin/reset.sh", "--non-interactive"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    return redirect(url_for("index"))


@app.route("/systemd-summary", methods=["GET"])
def systemd_summary_route() -> str:
    env = os.environ.copy()
    try:
        output = subprocess.check_output(
            ["/usr/local/bin/systemd-summary.sh"],
            env=env,
            text=True,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        output = exc.output
    return f"<pre>{output}</pre><p><a href='{url_for('index')}'>Back</a></p>"


@app.route("/teardown", methods=["POST"])
def teardown_route() -> Response | tuple[str, int]:
    if TEARDOWN_PATH is None:
        return "Error: TEARDOWN_PATH is not set", 500

    env = os.environ.copy()
    subprocess.Popen(
        [TEARDOWN_PATH, "--force", "--all"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    return redirect(url_for("index"))


@app.route("/stop-service", methods=["POST"])
def stop_service_route() -> Response:
    env = os.environ.copy()
    service = request.form.get("service")
    if service:
        run_bootstrap(["--stop-service", service], env=env, suppress=False)
    return redirect(url_for("index"))


@app.route("/start-service", methods=["POST"])
def start_service_route() -> Response:
    env = os.environ.copy()
    svc = request.form.get("service")
    if svc:
        env.update({"ACTION_FLAG": "--start", "ACTION_CONTAINER": svc})
        run_bootstrap(env=env, suppress=False)
    return redirect(url_for("index"))


@app.route("/restart-service", methods=["POST"])
def restart_service_route() -> Response:
    env = os.environ.copy()
    svc = request.form.get("service")
    if svc:
        env.update({"ACTION_FLAG": "--restart", "ACTION_CONTAINER": svc})
        run_bootstrap(env=env, suppress=False)
    return redirect(url_for("index"))


@app.route("/remove-service", methods=["POST"])
def remove_service_route() -> Response:
    env = os.environ.copy()
    svc = request.form.get("service")
    if svc:
        env.update({"ACTION_FLAG": "--remove", "ACTION_CONTAINER": svc})
        run_bootstrap(env=env, suppress=False)
    return redirect(url_for("index"))


@app.route("/add-service", methods=["POST"])
def add_service_route() -> Response:
    svc = request.form.get("service")
    image = request.form.get("image")
    port = request.form.get("port")
    desc = request.form.get("description")

    if svc and image and port and desc:
        # Create service configuration file directly
        services_dir = os.path.join(os.path.dirname(__file__), "..", "services", "user")
        os.makedirs(services_dir, exist_ok=True)

        config_file = os.path.join(services_dir, f"{svc}.conf")

        # Create backup if file exists
        if os.path.exists(config_file):
            backup_file = f"{config_file}.{int(time.time())}.bak"
            shutil.copy2(config_file, backup_file)

        # Write new configuration
        with open(config_file, "w") as f:
            f.write(f"image={image}\n")
            f.write(f"port={port}\n")
            f.write(f"description={desc}\n")
            f.write("service_type=docker\n")

        # Create config directory
        config_dir = os.path.join(os.path.dirname(__file__), "..", "docker-stack", f"{svc}-config")
        os.makedirs(config_dir, exist_ok=True)

        readme_file = os.path.join(config_dir, "README.md")
        if not os.path.exists(readme_file):
            with open(readme_file, "w") as f:
                f.write(f"# {svc} configuration\n")

    return redirect(url_for("index"))


@app.route("/logs/", defaults={"target": None})
@app.route("/logs/<path:target>")
def logs_index(target: str | None = None) -> Response | str:
    """List log files or show logs for a specific container."""
    if target:
        log_path = os.path.join(LOGS_DIR, target)
        if os.path.isfile(log_path):
            return send_from_directory(LOGS_DIR, target)

        # Fallback to docker logs for container names
        lines = request.args.get("lines", "100")
        try:
            output = subprocess.check_output(
                ["docker", "logs", "--tail", str(lines), target],
                text=True,
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as exc:
            output = exc.output
        escaped_output = html.escape(output)
        return f"<pre>{escaped_output}</pre><p><a href='{url_for('index')}'>Back</a></p>"

    files = sorted(os.listdir(LOGS_DIR)) if os.path.isdir(LOGS_DIR) else []
    links = "<br>".join(
        f'<a href="{url_for("logs_index", target=html.escape(f))}">{html.escape(f)}</a>'
        for f in files
    )
    return f"<h1>Logs</h1>{links}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
