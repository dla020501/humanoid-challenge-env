#!/usr/bin/env bash
# 참가자 이미지를 이 머신에서 만든다. 이 한 번이면 됩니다:
#
#   ./run/setup.sh                # 최신 오버레이로
#   ./run/setup.sh <주소나 파일>   # 특정 버전으로 (대회 공지에 주소가 있습니다)
#
# 하는 일: 대회 오버레이(코드+에셋)를 받아 풀고, docker build 한 번으로 Isaac Sim
# 바탕 이미지 받기(NVIDIA 레지스트리에서 직접 -- docker/.env 의 ACCEPT_EULA=Y 가
# 그 라이선스에 대한 본인의 동의입니다) + Isaac Lab 설치 + 대회 환경까지 이미지
# 하나로 만듭니다. Isaac Sim 을 따로 설치할 일은 없습니다.
# 처음에는 20~40 분 걸리고, 다시 실행하면 이미 받은 층은 캐시로 건너뜁니다.
set -euo pipefail

DEFAULT_URL="https://github.com/kairobahq/humanoid-challenge-env/releases/latest/download/challenge-overlay.tar.gz"
SRC="${1:-$DEFAULT_URL}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$HERE/../docker"
TAG="$(grep -oP '^CHALLENGE_IMAGE=\K.*' "$DOCKER_DIR/.env")"

case "$SRC" in
  http://*|https://*)
    echo "[1/3] 오버레이를 받는다: $SRC"
    curl -fL -o "$DOCKER_DIR/challenge-overlay.tar.gz" "$SRC"
    SRC="$DOCKER_DIR/challenge-overlay.tar.gz"
    ;;
  *)
    echo "[1/3] 오버레이: $SRC"
    [ -f "$SRC" ] || { echo "파일이 없다: $SRC" >&2; exit 1; }
    ;;
esac

echo "[2/3] stage 에 푼다"
rm -rf "$DOCKER_DIR/stage"
mkdir -p "$DOCKER_DIR/stage"
tar -xzf "$SRC" -C "$DOCKER_DIR/stage"

echo "[3/3] docker build -t $TAG  (20~40 분)"
# DOCKER_BUILD_FLAGS: 필요할 때만 추가 플래그 (예: DOCKER_BUILD_FLAGS=--no-cache)
docker build ${DOCKER_BUILD_FLAGS:-} -t "$TAG" -f "$DOCKER_DIR/Dockerfile" "$DOCKER_DIR"
echo
echo "완료. 이제:  cd docker && docker compose up -d && docker exec -it challenge_env bash"
