#!/usr/bin/env bats

@test "custom DOCKER_NETWORK_NAME influences network cleanup" {
  run bash -c '
    set -e
    MODE=all
    DOCKER_NETWORK_NAME=custom-net
    NETWORKS=("$DOCKER_NETWORK_NAME")
    REMOVED_NETWORKS=()
    run(){ echo RUN:$*; }
    if [[ "$MODE" == "all" ]]; then
      for net in "${NETWORKS[@]}"; do
        run docker network rm "$net" || true && REMOVED_NETWORKS+=("$net")
      done
    fi
    echo removed ${REMOVED_NETWORKS[*]}
  '
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "RUN:docker network rm custom-net" ]
  [ "${lines[1]}" = "removed custom-net" ]
}
