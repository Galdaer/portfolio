import importlib.util
import os
import shutil
from pathlib import Path
import subprocess
import warnings
import sys
import types

import pytest

# Load config_web_ui.py as a module
SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "config_web_ui.py"
spec = importlib.util.spec_from_file_location("config_web_ui", SCRIPT_PATH)
config_web_ui = importlib.util.module_from_spec(spec)

# Stub minimal flask module to satisfy imports
flask_stub = types.ModuleType("flask")
class _Flask:
    def __init__(self, *args, **kwargs):
        pass
    def route(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def run(self, *args, **kwargs):
        pass
flask_stub.Flask = _Flask
flask_stub.request = object
flask_stub.redirect = lambda *a, **k: None
flask_stub.url_for = lambda *a, **k: ""
flask_stub.render_template_string = lambda *a, **k: ""
flask_stub.send_from_directory = lambda *a, **k: None
sys.modules.setdefault("flask", flask_stub)

spec.loader.exec_module(config_web_ui)

key_to_service = config_web_ui.key_to_service
changed_services = config_web_ui.changed_services
SERVICE_PREFIX_MAP = config_web_ui.SERVICE_PREFIX_MAP


def test_key_to_service_basic():
    for prefix, service in SERVICE_PREFIX_MAP.items():
        assert key_to_service(f"{prefix}_PORT") == service

    assert key_to_service("CONTAINER_PORTS[grafana]") == "grafana"

    assert key_to_service("UNKNOWN_PORT") is None


def test_changed_services_detection():
    old = {
        "CONTAINER_PORTS[grafana]": "3000",
        "PLEX_PORT": "32400",
        "OTHER_VAR": "foo",
    }
    new = {
        "CONTAINER_PORTS[grafana]": "4000",  # changed -> grafana
        "PLEX_PORT": "32400",     # unchanged
        "OTHER_VAR": "bar",       # not mapped
    }
    result = changed_services(old, new)
    assert result == {"grafana"}


def test_build_service_prefix_map_basic(tmp_path, monkeypatch):
    root = tmp_path
    (root / "services" / "core").mkdir(parents=True)
    (root / "services" / "user").mkdir(parents=True)
    (root / "services" / "core" / "foo.conf").write_text("")
    (root / "services" / "core" / "foobar.conf").write_text("")
    (root / "services" / "user" / "bar.conf").write_text("")
    monkeypatch.setattr(config_web_ui, "__file__", str(root / "scripts" / "config_web_ui.py"))
    prefix_map = config_web_ui.build_service_prefix_map()
    assert list(prefix_map.keys()) == ["FOOBAR", "FOO", "BAR"]
    assert prefix_map == {"FOOBAR": "foobar", "FOO": "foo", "BAR": "bar"}


def test_build_service_prefix_map_duplicate_warning(tmp_path, monkeypatch):
    root = tmp_path
    (root / "services" / "core").mkdir(parents=True)
    (root / "services" / "user").mkdir(parents=True)
    (root / "services" / "core" / "foo.conf").write_text("")
    (root / "services" / "user" / "foo.conf").write_text("")
    monkeypatch.setattr(config_web_ui, "__file__", str(root / "scripts" / "config_web_ui.py"))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        prefix_map = config_web_ui.build_service_prefix_map()
    assert prefix_map == {"FOO": "foo"}
    assert any("Duplicate service config" in str(w.message) for w in rec)


def test_port_loaded_from_env(monkeypatch):
    monkeypatch.setenv("CONFIG_WEB_UI_PORT", "12345")
    spec_local = importlib.util.spec_from_file_location("config_web_ui_reload", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec_local)
    spec_local.loader.exec_module(mod)
    assert mod.PORT == 12345


def test_teardown_path_from_env(monkeypatch):
    monkeypatch.setenv("TEARDOWN_PATH", "/tmp/custom-teardown.sh")
    spec_local = importlib.util.spec_from_file_location("config_web_ui_reload", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec_local)
    spec_local.loader.exec_module(mod)
    assert mod.TEARDOWN_PATH == "/tmp/custom-teardown.sh"


def test_teardown_path_fallback_to_which(monkeypatch):
    monkeypatch.delenv("TEARDOWN_PATH", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _name: "/opt/intelluxe/scripts/teardown.sh")
    spec_local = importlib.util.spec_from_file_location("config_web_ui_reload", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec_local)
    spec_local.loader.exec_module(mod)
    assert mod.TEARDOWN_PATH == "/opt/intelluxe/scripts/teardown.sh"


def test_teardown_path_default(monkeypatch):
    monkeypatch.delenv("TEARDOWN_PATH", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    spec_local = importlib.util.spec_from_file_location("config_web_ui_reload", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec_local)
    spec_local.loader.exec_module(mod)
    assert mod.TEARDOWN_PATH == "/usr/local/bin/clinic-teardown.sh"


def test_bootstrap_route_invokes_subprocess(monkeypatch):
    calls = {}

    def fake_popen(cmd, stdout=None, stderr=None, env=None):
        calls['cmd'] = cmd
        calls['stdout'] = stdout
        calls['stderr'] = stderr
        calls['env'] = env
        class Dummy:  # noqa: D401
            pass
        return Dummy()

    monkeypatch.setattr(config_web_ui.subprocess, 'Popen', fake_popen)

    redirect_args = {}

    def fake_redirect(url):
        redirect_args['url'] = url
        return f"redirect to {url}"

    monkeypatch.setattr(config_web_ui, 'url_for', lambda endpoint: f"/{endpoint}")
    monkeypatch.setattr(config_web_ui, 'redirect', fake_redirect)

    expected_env = os.environ.copy()
    result = config_web_ui.bootstrap()

    assert calls['cmd'] == [config_web_ui.BOOTSTRAP_PATH, "--non-interactive"]
    assert calls['stdout'] is subprocess.DEVNULL
    assert calls['stderr'] is subprocess.DEVNULL
    assert calls['env'] == expected_env
    assert redirect_args['url'] == '/index'
    assert result == 'redirect to /index'


def test_reset_wg_keys_route(monkeypatch):
    calls = {}

    def fake_popen(cmd, stdout=None, stderr=None, env=None):
        calls['cmd'] = cmd
        calls['stdout'] = stdout
        calls['stderr'] = stderr
        calls['env'] = env
        class Dummy:
            pass
        return Dummy()

    monkeypatch.setattr(config_web_ui.subprocess, 'Popen', fake_popen)

    redirect_args = {}

    def fake_redirect(url):
        redirect_args['url'] = url
        return f"redirect to {url}"

    monkeypatch.setattr(config_web_ui, 'url_for', lambda endpoint: f"/{endpoint}")
    monkeypatch.setattr(config_web_ui, 'redirect', fake_redirect)

    expected_env = os.environ.copy()
    result = config_web_ui.reset_wg_keys()

    assert calls['cmd'] == [config_web_ui.BOOTSTRAP_PATH, "--non-interactive", "--reset-wg-keys"]
    assert calls['stdout'] is subprocess.DEVNULL
    assert calls['stderr'] is subprocess.DEVNULL
    assert calls['env'] == expected_env
    assert redirect_args['url'] == '/index'
    assert result == 'redirect to /index'


def _route_test(
    monkeypatch,
    func,
    expected_cmd,
    env_updates=None,
    form_service=None,
    expect_suppress=True,
):
    calls = {}

    def fake_popen(cmd, stdout=None, stderr=None, env=None):
        calls['cmd'] = cmd
        calls['stdout'] = stdout
        calls['stderr'] = stderr
        calls['env'] = env
        class Dummy:
            pass
        return Dummy()

    monkeypatch.setattr(config_web_ui.subprocess, 'Popen', fake_popen)
    redirect_args = {}

    def fake_redirect(url):
        redirect_args['url'] = url
        return f"redirect to {url}"

    monkeypatch.setattr(config_web_ui, 'url_for', lambda endpoint, **kw: f"/{endpoint}")
    monkeypatch.setattr(config_web_ui, 'redirect', fake_redirect)

    if form_service is not None:
        req = types.SimpleNamespace(form=types.SimpleNamespace(get=lambda k: form_service))
        monkeypatch.setattr(config_web_ui, 'request', req)

    expected_env = os.environ.copy()
    if env_updates:
        expected_env.update(env_updates)

    result = func()

    assert calls['cmd'] == expected_cmd
    if expect_suppress:
        assert calls['stdout'] is subprocess.DEVNULL
        assert calls['stderr'] is subprocess.DEVNULL
    else:
        assert calls['stdout'] is None
        assert calls['stderr'] is None
    assert calls.get('env') == expected_env
    assert redirect_args['url'] == '/index'
    assert result == 'redirect to /index'


def test_self_update_route(monkeypatch):
    _route_test(
        monkeypatch,
        config_web_ui.self_update,
        [config_web_ui.BOOTSTRAP_PATH, "--non-interactive", "--self-update"],
    )


def test_diagnostics_route(monkeypatch):
    _route_test(
        monkeypatch,
        config_web_ui.diagnostics,
        ["/usr/local/bin/clinic-diagnostics.sh", "--non-interactive"],
    )


def test_auto_repair_route(monkeypatch):
    _route_test(
        monkeypatch,
        config_web_ui.auto_repair,
        ["/usr/local/bin/clinic-auto-repair.sh", "--non-interactive"],
    )


def test_reset_system_route(monkeypatch):
    _route_test(
        monkeypatch,
        config_web_ui.reset_system_route,
        ["/usr/local/bin/clinic-reset.sh", "--non-interactive"],
    )


def test_teardown_route(monkeypatch):
    _route_test(
        monkeypatch,
        config_web_ui.teardown_route,
        [config_web_ui.TEARDOWN_PATH, "--force", "--all"],
    )


def test_systemd_summary_route(monkeypatch):
    calls = {}

    def fake_check_output(cmd, env=None, text=False, stderr=None):
        calls['cmd'] = cmd
        calls['env'] = env
        calls['text'] = text
        calls['stderr'] = stderr
        return "summary output"

    monkeypatch.setattr(config_web_ui.subprocess, 'check_output', fake_check_output)
    monkeypatch.setattr(config_web_ui, 'url_for', lambda endpoint: '/index')
    result = config_web_ui.systemd_summary_route()

    assert calls['cmd'] == ["/usr/local/bin/systemd-summary.sh"]
    assert calls['env'] == os.environ.copy()
    assert calls['text'] is True
    assert calls['stderr'] == subprocess.STDOUT
    assert result == "<pre>summary output</pre><p><a href='/index'>Back</a></p>"


def test_systemd_summary_route_error(monkeypatch):
    def raise_error(*_args, **_kwargs):
        raise subprocess.CalledProcessError(1, "cmd", output="fail")

    monkeypatch.setattr(config_web_ui.subprocess, 'check_output', raise_error)
    monkeypatch.setattr(config_web_ui, 'url_for', lambda endpoint: '/index')
    result = config_web_ui.systemd_summary_route()
    assert result == "<pre>fail</pre><p><a href='/index'>Back</a></p>"


def test_stop_service_route_no_service(monkeypatch):
    calls = {"called": False}

    def fake_run_bootstrap(*_args, **_kwargs):
        calls["called"] = True

    monkeypatch.setattr(config_web_ui, "run_bootstrap", fake_run_bootstrap)
    monkeypatch.setattr(config_web_ui, "url_for", lambda e: "/index")
    monkeypatch.setattr(config_web_ui, "redirect", lambda u: f"redirect to {u}")
    req = types.SimpleNamespace(form=types.SimpleNamespace(get=lambda k: None))
    monkeypatch.setattr(config_web_ui, "request", req)
    result = config_web_ui.stop_service_route()
    assert calls["called"] is False
    assert result == "redirect to /index"


def test_index_contains_reset_form(monkeypatch):
    monkeypatch.setattr(
        config_web_ui,
        'load_config',
        lambda: {'SELECTED_CONTAINERS': [], 'CONTAINER_PORTS[grafana]': '1234'},
    )
    monkeypatch.setattr(config_web_ui, 'get_all_containers', lambda: [])
    monkeypatch.setattr(config_web_ui, 'render_template_string',
                        lambda tpl, **kw: tpl.replace("{{ grafana_port }}", kw.get('grafana_port', '')))
    req = types.SimpleNamespace(method='GET', form=types.SimpleNamespace(get=lambda *a, **k: None, getlist=lambda *a, **k: []))
    monkeypatch.setattr(config_web_ui, 'request', req)
    def fake_url_for(endpoint):
        if endpoint == 'teardown_route':
            return '/teardown'
        return '/' + endpoint.replace('_', '-')

    monkeypatch.setattr(config_web_ui, 'url_for', fake_url_for)
    html = config_web_ui.index()
    assert 'Reset WireGuard Keys' in html
    assert 'reset_wg_keys' in html
    assert 'Grafana Dashboard' in html
    assert 'http://localhost:1234' in html


def test_index_contains_teardown_form(monkeypatch):
    pytest.importorskip("jinja2")
    monkeypatch.setattr(
        config_web_ui,
        'load_config',
        lambda: {'SELECTED_CONTAINERS': [], 'CONTAINER_PORTS[grafana]': '3001'},
    )
    monkeypatch.setattr(config_web_ui, 'get_all_containers', lambda: [])
    def render(tpl, **kw):
        import jinja2
        return jinja2.Template(tpl).render(url_for=config_web_ui.url_for, **kw)

    monkeypatch.setattr(config_web_ui, 'render_template_string', render)
    req = types.SimpleNamespace(method='GET', form=types.SimpleNamespace(get=lambda *a, **k: None, getlist=lambda *a, **k: []))
    monkeypatch.setattr(config_web_ui, 'request', req)
    def fake_url_for(endpoint):
        if endpoint == 'teardown_route':
            return '/teardown'
        return '/' + endpoint.replace('_', '-')

    monkeypatch.setattr(config_web_ui, 'url_for', fake_url_for)
    html = config_web_ui.index()
    assert 'Run Teardown' in html
    assert 'action="/teardown"' in html
    assert "confirm('Teardown entire stack?')" in html


def test_index_default_grafana_port(monkeypatch):
    monkeypatch.setattr(
        config_web_ui,
        'load_config',
        lambda: {'SELECTED_CONTAINERS': []},
    )
    monkeypatch.setattr(config_web_ui, 'get_all_containers', lambda: [])
    monkeypatch.setattr(config_web_ui, 'render_template_string',
                        lambda tpl, **kw: tpl.replace("{{ grafana_port }}", kw.get('grafana_port', '')))
    req = types.SimpleNamespace(method='GET', form=types.SimpleNamespace(get=lambda *a, **k: None, getlist=lambda *a, **k: []))
    monkeypatch.setattr(config_web_ui, 'request', req)
    monkeypatch.setattr(config_web_ui, 'url_for', lambda e: '/' + e.replace('_', '-'))
    html = config_web_ui.index()
    assert 'Grafana Dashboard' in html
    assert 'http://localhost:3001' in html


def test_get_grafana_default_port_file(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    script_dir = root / "scripts"
    script_dir.mkdir(parents=True)
    monkeypatch.setattr(config_web_ui, "__file__", str(script_dir / "config_web_ui.py"))
    conf_dir = root / "services" / "core"
    conf_dir.mkdir(parents=True)
    (conf_dir / "grafana.conf").write_text("port=5678\n")
    port = config_web_ui.get_grafana_default_port()
    assert port == "5678"


def test_get_grafana_default_port_missing(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    script_dir = root / "scripts"
    script_dir.mkdir(parents=True)
    monkeypatch.setattr(config_web_ui, "__file__", str(script_dir / "config_web_ui.py"))
    port = config_web_ui.get_grafana_default_port()
    assert port == "3001"


def test_parse_all_containers(tmp_path, monkeypatch):
    script = tmp_path / "bootstrap.sh"
    script.write_text("ALL_CONTAINERS=(a b c)\n")
    monkeypatch.setattr(config_web_ui, "BOOTSTRAP_PATH", str(script))
    assert config_web_ui.get_all_containers() == ["a", "b", "c"]


def test_load_and_save_selected_containers(tmp_path, monkeypatch):
    cfg = tmp_path / "conf"
    cfg.write_text("SELECTED_CONTAINERS=(traefik wireguard)\nOTHER=1\n")
    monkeypatch.setattr(config_web_ui, "CONFIG_FILE", str(cfg))
    monkeypatch.setenv("CFG_UID", "123")
    monkeypatch.setenv("CFG_GID", "456")
    chown_args = {}

    def fake_chown(path, uid, gid):
        chown_args["path"] = path
        chown_args["uid"] = uid
        chown_args["gid"] = gid

    monkeypatch.setattr(config_web_ui.os, "chown", fake_chown)
    data = config_web_ui.load_config()
    assert data["SELECTED_CONTAINERS"] == ["traefik", "wireguard"]
    data["SELECTED_CONTAINERS"] = ["wireguard"]
    config_web_ui.save_config(data)
    text = cfg.read_text()
    assert "SELECTED_CONTAINERS=(wireguard)" in text
    assert chown_args == {
        "path": str(cfg),
        "uid": 123,
        "gid": 456,
    }


def test_save_config_chown_default_uid_gid(tmp_path, monkeypatch):
    cfg = tmp_path / "conf"
    cfg.write_text("SELECTED_CONTAINERS=()\n")
    monkeypatch.setattr(config_web_ui, "CONFIG_FILE", str(cfg))
    monkeypatch.delenv("CFG_UID", raising=False)
    monkeypatch.delenv("CFG_GID", raising=False)
    chown_args = {}

    def fake_chown(path, uid, gid):
        chown_args["path"] = path
        chown_args["uid"] = uid
        chown_args["gid"] = gid

    monkeypatch.setattr(config_web_ui.os, "chown", fake_chown)
    data = config_web_ui.load_config()
    config_web_ui.save_config(data)
    assert chown_args == {
        "path": str(cfg),
        "uid": 1000,
        "gid": 1000,
    }


def test_index_includes_extra_fields(monkeypatch):
    cfg = {field: "x" for field in config_web_ui.EXTRA_FIELDS}
    cfg["SELECTED_CONTAINERS"] = []
    monkeypatch.setattr(config_web_ui, "load_config", lambda: cfg)
    monkeypatch.setattr(config_web_ui, "get_all_containers", lambda: [])
    def fake_render_template_string(tpl, **kw):
        return "\n".join(f'<input name="{k}">' for k in kw["config"].keys())
    monkeypatch.setattr(config_web_ui, "render_template_string", fake_render_template_string)
    req = types.SimpleNamespace(method="GET", form=types.SimpleNamespace(get=lambda *a, **k: None, getlist=lambda *a, **k: []))
    monkeypatch.setattr(config_web_ui, "request", req)
    html = config_web_ui.index()
    for field in config_web_ui.EXTRA_FIELDS:
        assert f'name="{field}"' in html


def test_index_post_updates_extra_fields(monkeypatch):
    start = {field: "old" for field in config_web_ui.EXTRA_FIELDS}
    start["SELECTED_CONTAINERS"] = []
    monkeypatch.setattr(config_web_ui, "load_config", lambda: start)
    monkeypatch.setattr(config_web_ui, "get_all_containers", lambda: [])
    monkeypatch.setattr(config_web_ui.subprocess, "Popen", lambda *a, **k: None)
    monkeypatch.setattr(config_web_ui, "changed_services", lambda a, b: set())
    saved = {}

    def fake_save(data):
        saved.update(data)

    monkeypatch.setattr(config_web_ui, "save_config", fake_save)
    monkeypatch.setattr(config_web_ui, "url_for", lambda e: "/index")
    monkeypatch.setattr(config_web_ui, "redirect", lambda u: f"redirect to {u}")
    form_data = {field: "new" for field in config_web_ui.EXTRA_FIELDS}
    form_data["SELECTED_CONTAINERS"] = []
    req = types.SimpleNamespace(
        method="POST",
        form=types.SimpleNamespace(
            get=lambda k, d=None: form_data.get(k, d),
            getlist=lambda k: form_data.get(k, []),
        ),
    )
    monkeypatch.setattr(config_web_ui, "request", req)
    result = config_web_ui.index()
    assert saved == form_data
    assert result == "redirect to /index"


def test_logs_index_lists_files(monkeypatch):
    monkeypatch.setattr(config_web_ui.os.path, "isdir", lambda p: True)
    monkeypatch.setattr(config_web_ui.os, "listdir", lambda p: ["a.log", "b.log"])

    calls = []

    def fake_url_for(endpoint, target=None):
        calls.append((endpoint, target))
        return f"/logs/{target or ''}"

    monkeypatch.setattr(config_web_ui, "url_for", fake_url_for)

    def _fail(*args, **kwargs):
        raise AssertionError("send_from_directory should not be called")

    monkeypatch.setattr(config_web_ui, "send_from_directory", _fail)
    html = config_web_ui.logs_index()
    assert calls == [("logs_index", "a.log"), ("logs_index", "b.log")]
    assert "<h1>Logs</h1>" in html
    assert 'href="/logs/a.log"' in html
    assert 'href="/logs/b.log"' in html


def test_logs_index_serves_file(monkeypatch):
    result_obj = object()
    called = {}

    def fake_send(dirpath, fname):
        called["dirpath"] = dirpath
        called["fname"] = fname
        return result_obj

    monkeypatch.setattr(config_web_ui, "send_from_directory", fake_send)
    monkeypatch.setattr(config_web_ui.os.path, "isfile", lambda p: True)
    returned = config_web_ui.logs_index("foo.log")
    assert called == {"dirpath": config_web_ui.LOGS_DIR, "fname": "foo.log"}
    assert returned is result_obj


def test_logs_index_missing_dir(monkeypatch):
    monkeypatch.setattr(config_web_ui.os.path, "isdir", lambda p: False)

    called = {}

    def fake_listdir(_p):
        called["listdir"] = True
        return []

    monkeypatch.setattr(config_web_ui.os, "listdir", fake_listdir)

    def _fail(*args, **kwargs):
        raise AssertionError("send_from_directory should not be called")

    monkeypatch.setattr(config_web_ui, "send_from_directory", _fail)
    html = config_web_ui.logs_index()
    assert "<h1>Logs</h1>" in html
    assert called == {}


def test_logs_index_container_logs(monkeypatch):
    monkeypatch.setattr(config_web_ui.os.path, "isfile", lambda p: False)
    req = types.SimpleNamespace(args={"lines": "5"})
    monkeypatch.setattr(config_web_ui, "request", req)
    monkeypatch.setattr(config_web_ui, "url_for", lambda e: "/index")
    calls = {}

    def fake_check_output(cmd, text=False, stderr=None):
        calls["cmd"] = cmd
        calls["text"] = text
        calls["stderr"] = stderr
        return "log output"

    monkeypatch.setattr(config_web_ui.subprocess, "check_output", fake_check_output)
    html = config_web_ui.logs_index("svc")
    assert calls["cmd"] == ["docker", "logs", "--tail", "5", "svc"]
    assert "<pre>log output</pre>" in html


def test_logs_index_container_logs_error(monkeypatch):
    monkeypatch.setattr(config_web_ui.os.path, "isfile", lambda p: False)
    req = types.SimpleNamespace(args={"lines": "7"})
    monkeypatch.setattr(config_web_ui, "request", req)
    monkeypatch.setattr(config_web_ui, "url_for", lambda e: "/index")

    def fake_check_output(cmd, text=False, stderr=None):
        exc = subprocess.CalledProcessError(1, cmd, output="err output")
        raise exc

    monkeypatch.setattr(config_web_ui.subprocess, "check_output", fake_check_output)
    html = config_web_ui.logs_index("svc")
    assert "<pre>err output</pre>" in html


def test_logs_index_container_logs_html_escaped(monkeypatch):
    monkeypatch.setattr(config_web_ui.os.path, "isfile", lambda p: False)
    req = types.SimpleNamespace(args={"lines": "1"})
    monkeypatch.setattr(config_web_ui, "request", req)
    monkeypatch.setattr(config_web_ui, "url_for", lambda e: "/index")

    def fake_check_output(cmd, text=False, stderr=None):
        return "<tag>"

    monkeypatch.setattr(config_web_ui.subprocess, "check_output", fake_check_output)
    html = config_web_ui.logs_index("svc")
    assert "<pre>&lt;tag&gt;</pre>" in html


def test_add_service_route(monkeypatch, tmp_path):
    form_data = {
        "service": "newsvc",
        "image": "my/image",
        "port": "1234",
        "description": "desc",
    }

    # Mock the services directory
    services_dir = tmp_path / "services" / "user"
    services_dir.mkdir(parents=True)

    # Mock the config directory
    config_dir = tmp_path / "docker-stack"
    config_dir.mkdir(parents=True)

    # Store the original os.path.join before patching to avoid recursion
    original_join = config_web_ui.os.path.join

    # Patch the paths - fix recursion issue
    def safe_path_join(*args):
        if len(args) <= 1:
            return str(tmp_path)
        # Don't use tmp_path if the first arg is already the tmp_path
        first_arg = str(args[0]) if args else ""
        if str(tmp_path) in first_arg:
            return original_join(*[str(arg) for arg in args])
        else:
            return original_join(str(tmp_path), *[str(arg) for arg in args[1:]])

    monkeypatch.setattr(config_web_ui.os.path, 'join', safe_path_join)
    monkeypatch.setattr(config_web_ui.os, 'makedirs', lambda path, exist_ok=False: None)

    files_created = {}
    file_contents = {}

    def fake_open(filename, mode='r'):
        if 'w' in mode:
            files_created[filename] = True
            return MockFileWrite(filename, file_contents)
        return MockFileRead(filename, file_contents)

    monkeypatch.setattr("builtins.open", fake_open)

    redirect_args = {}

    def fake_redirect(url):
        redirect_args["url"] = url
        return f"redirect to {url}"

    monkeypatch.setattr(config_web_ui, "url_for", lambda e: "/index")
    monkeypatch.setattr(config_web_ui, "redirect", fake_redirect)

    req = types.SimpleNamespace(
        form=types.SimpleNamespace(get=lambda k, d=None: form_data.get(k, d))
    )
    monkeypatch.setattr(config_web_ui, "request", req)

    result = config_web_ui.add_service_route()

    # Verify configuration file was created with correct content
    config_file = str(tmp_path / "newsvc.conf")
    assert config_file in file_contents

    config_content = file_contents[config_file]
    assert "image=my/image\n" in config_content
    assert "port=1234\n" in config_content
    assert "description=desc\n" in config_content
    assert "service_type=docker\n" in config_content

    assert redirect_args["url"] == "/index"
    assert result == "redirect to /index"


class MockFileWrite:
    def __init__(self, filename, file_contents):
        self.filename = filename
        self.file_contents = file_contents

    def write(self, content):
        if self.filename not in self.file_contents:
            self.file_contents[self.filename] = ""
        self.file_contents[self.filename] += content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockFileRead:
    def __init__(self, filename, file_contents):
        self.filename = filename
        self.file_contents = file_contents

    def read(self):
        return self.file_contents.get(self.filename, "")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@pytest.mark.parametrize("missing_field", [
    "service",
    "image",
    "port",
    "description",
])
def test_add_service_route_missing_field(monkeypatch, missing_field):
    form_data = {
        "service": "newsvc",
        "image": "my/image",
        "port": "1234",
        "description": "desc",
    }

    popen_calls = {}

    def fake_popen(*_args, **_kwargs):
        popen_calls["popen"] = True

    monkeypatch.setattr(config_web_ui.subprocess, "Popen", fake_popen)

    redirect_args = {}

    def fake_redirect(url):
        redirect_args["url"] = url
        return f"redirect to {url}"

    monkeypatch.setattr(config_web_ui, "url_for", lambda e: "/index")
    monkeypatch.setattr(config_web_ui, "redirect", fake_redirect)

    def get_missing_field(key, default=None):
        if key == missing_field:
            return None
        return form_data.get(key, default)

    req = types.SimpleNamespace(
        form=types.SimpleNamespace(get=get_missing_field)
    )
    monkeypatch.setattr(config_web_ui, "request", req)

    result = config_web_ui.add_service_route()

    assert popen_calls == {}
    assert redirect_args["url"] == "/index"
    assert result == "redirect to /index"


def test_index_includes_add_service_form(monkeypatch):
    monkeypatch.setattr(config_web_ui, "load_config", lambda: {"SELECTED_CONTAINERS": []})
    monkeypatch.setattr(config_web_ui, "get_all_containers", lambda: [])
    monkeypatch.setattr(config_web_ui, "render_template_string", lambda tpl, **kw: tpl)
    req = types.SimpleNamespace(method="GET", form=types.SimpleNamespace(get=lambda *a, **k: None, getlist=lambda *a, **k: []))
    monkeypatch.setattr(config_web_ui, "request", req)
    monkeypatch.setattr(config_web_ui, "url_for", lambda e: f"/{e}")
    html = config_web_ui.index()
    assert "addServiceForm" in html


def test_index_includes_remove_service_form(monkeypatch):
    monkeypatch.setattr(config_web_ui, "load_config", lambda: {"SELECTED_CONTAINERS": []})
    monkeypatch.setattr(config_web_ui, "get_all_containers", lambda: [])
    monkeypatch.setattr(config_web_ui, "render_template_string", lambda tpl, **kw: tpl)
    req = types.SimpleNamespace(method="GET", form=types.SimpleNamespace(get=lambda *a, **k: None, getlist=lambda *a, **k: []))
    monkeypatch.setattr(config_web_ui, "request", req)
    monkeypatch.setattr(config_web_ui, "url_for", lambda e: f"/{e}")
    html = config_web_ui.index()
    assert "removeForm" in html


def test_add_service_form_confirm_js(tmp_path):
    if shutil.which("node") is None:
        pytest.skip("node binary not available")
    js_path = Path(__file__).resolve().parents[2] / "test" / "javascript" / "test_add_service_confirm.js"
    result = subprocess.run(["node", str(js_path)], capture_output=True, text=True)
    assert result.stdout.strip() == "PASS"


def test_get_container_statuses_parses(monkeypatch):
    output = "svc1 Up 10 seconds\nsvc2 Exited (0) 1 minute ago\n"
    monkeypatch.setattr(
        config_web_ui.subprocess,
        "check_output",
        lambda *a, **k: output,
    )
    status = config_web_ui.get_container_statuses()
    assert status == {
        "svc1": "Up 10 seconds",
        "svc2": "Exited (0) 1 minute ago",
    }


def test_get_container_statuses_error(monkeypatch):
    def _raise(*_a, **_k):
        raise subprocess.CalledProcessError(1, ["docker"])

    monkeypatch.setattr(config_web_ui.subprocess, "check_output", _raise)
    assert config_web_ui.get_container_statuses() == {}


def test_index_passes_container_status(monkeypatch):
    monkeypatch.setattr(config_web_ui, "load_config", lambda: {"SELECTED_CONTAINERS": []})
    monkeypatch.setattr(config_web_ui, "get_all_containers", lambda: ["svc1"])
    statuses = {"svc1": "Up"}
    monkeypatch.setattr(config_web_ui, "get_container_statuses", lambda: statuses)
    req = types.SimpleNamespace(method="GET", form=types.SimpleNamespace(get=lambda *a, **k: None, getlist=lambda *a, **k: []))
    monkeypatch.setattr(config_web_ui, "request", req)
    monkeypatch.setattr(config_web_ui, "url_for", lambda e: f"/{e}")
    captured = {}

    def fake_render(tpl, **kw):
        captured.update(kw)
        return "OK"

    monkeypatch.setattr(config_web_ui, "render_template_string", fake_render)
    result = config_web_ui.index()
    assert captured["container_status"] == statuses
    assert result == "OK"

