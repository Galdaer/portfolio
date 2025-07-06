#!/usr/bin/env bats

@test "config-web-ui.service uses EnvironmentFile" {
  grep -q '^EnvironmentFile=/opt/intelluxe/clinic-stack/.clinic-bootstrap.conf' systemd/config-web-ui.service
}

