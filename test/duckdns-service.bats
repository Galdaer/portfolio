#!/usr/bin/env bats

@test "duckdns-update service expands CFG_ROOT" {
  line=$(grep '^EnvironmentFile=' systemd/duckdns-update.service | tail -n1)
  path=${line#EnvironmentFile=}
  path=${path#-}
  export CFG_ROOT=/tmp/testroot
  eval "expanded=$path"
  [ "$expanded" = "$CFG_ROOT/duckdns/duckdns.env" ]
}

