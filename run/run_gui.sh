#!/usr/bin/env bash
# GUI 로 기본 씬을 띄운다 -- 편의점 매장 전체에 로봇이 서 있는 그림.
# X11 세션의 호스트에서 실행할 것. 창이 뜨기까지 30~60 초 걸린다.
#
# 창을 닫으면 스크립트는 끝나지만 컨테이너는 떠 있다. 다른 씬(예: 과제 B 데모)은
# 컨테이너에 들어가 직접 돌리면 된다:
#   docker exec -it challenge_env bash
#   ${ISAACLAB_PATH}/_isaac_sim/python.sh -u /workspace/challenge_scripts/task_b_demo.py --seed 1000
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$HERE/../docker"

xhost +local:root
docker compose -f "$DOCKER_DIR/docker-compose.yaml" -f "$DOCKER_DIR/x11.yaml" up -d
echo "매장 기본 씬을 띄웁니다 -- Isaac Sim 창이 뜨기까지 30~60 초, 그동안 경고가 잔뜩 나옵니다 (정상)."
exec docker exec -it challenge_env bash -lc \
  'cd /workspace/cyclo_lab && ${ISAACLAB_PATH}/_isaac_sim/python.sh -u /workspace/challenge_scripts/basic_convstore.py'
