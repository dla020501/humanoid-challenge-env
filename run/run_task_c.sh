#!/usr/bin/env bash
# 과제 C 의 시작 장면을 GUI 로 한 번 세워 띄운다. X11 세션의 호스트에서 실행할 것.
# 창이 뜨기까지 30~60 초 걸리고 그동안 경고가 잔뜩 나온다. 정상이다.
# 다른 장면을 보려면 아래 SEED 를 바꾸거나, 컨테이너에 들어가 --seed 를 직접 준다.
set -euo pipefail
SEED=1000
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$HERE/../docker"

xhost +local:root
docker compose -f "$DOCKER_DIR/docker-compose.yaml" -f "$DOCKER_DIR/x11.yaml" up -d
echo "과제 C 씬(seed $SEED)을 띄웁니다 — 창이 뜨기까지 30~60 초."
exec docker exec -it challenge_env bash -lc \
  "cd /workspace/cyclo_lab && \${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
   /workspace/challenge_scripts/task_c_demo.py --seed $SEED"
