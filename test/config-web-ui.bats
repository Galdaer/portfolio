#!/usr/bin/env bats

@test "config-web-ui.service uses EnvironmentFile" {
  if [[ ! -f "systemd/config-web-ui.service" ]]; then
    skip "systemd/config-web-ui.service file not found"
  fi
  grep -q 'EnvironmentFile.*bootstrap\.conf' systemd/config-web-ui.service
}

