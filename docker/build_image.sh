#!/usr/bin/env bash
# 배포 이미지를 만든다.
#
#   ./build_image.sh /path/to/cstore-challenge [태그]
#
# 세 걸음이다.
#
#   1. 추린다   대회 환경 저장소에서 과제 B 에 필요한 것만 docker/stage/ 로 옮긴다.
#               아래 KEEP 배열이 "참가자에게 무엇을 주는가" 의 전부다.
#   2. 다시 깐다 에셋 트리를 배포용 이름으로 재배치하고(reshape_assets.py), 환경 코드의
#               경로 상수를 새 자리로 고친다(patch_paths.py). **원본 저장소는 건드리지
#               않는다** -- 고치는 것은 stage 안의 사본뿐이라, 수집·평가 파이프라인이
#               쓰는 경로는 그대로 남는다.
#   3. 굽는다   그 트리로 Dockerfile 을 빌드한다.
#
# 참가자는 이 스크립트를 쓸 일이 없다 -- 이미지는 받아서 쓰는 것이다. 이것은 대회 측이
# 그 이미지를 어떻게 만드는지에 대한 기록이자, 다시 만들 수 있게 하는 수단이다.
set -euo pipefail

SRC="${1:-}"
TAG="${2:-ghcr.io/kairobahq/humanoid-challenge-env:latest}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE="$HERE/stage"
BASE_IMAGE="${BASE_IMAGE:-nvcr.io/nvidia/isaac-sim:5.1.0}"

if [[ -z "$SRC" || ! -d "$SRC/source/cyclo_lab" ]]; then
  echo "사용법: $0 /path/to/cstore-challenge [태그]" >&2
  exit 1
fi
SRC="$(cd "$SRC" && pwd)"

# 이미지에 들어가는 것 전부. 경로는 대회 환경 저장소의 루트 기준.
#
# 여기에 **없는** 것 중 설명이 필요한 둘:
#   our_scan_data/          상품 36 개가 taskB_products/ 와 md5 단위로 겹치는 사본이다
#                           (2026-08-25 확인). 옛날에는 이것도 넣어야 상품에 색이 입었는데,
#                           skin USD 가 텍스처를 그쪽 절대경로로 물고 있었기 때문이다.
#                           reshape_assets.py 가 그 경로를 상대경로로 다시 쓰므로 이제
#                           사본 한 벌이면 된다. 200 MB 가 그대로 빠진다.
#   FFW_SH5 / OMY USD       과제 B 가 쓰지 않는 로봇이다. 93 MB.
KEEP=(
  # 라이선스 — README 의 고지가 가리키는 파일들
  LICENSE
  LICENSE-IsaacLab
  THIRD_PARTY_LICENSES.md

  # Isaac Lab (BSD-3-Clause, 원본 무수정)
  third_party/IsaacLab

  # 스워브 구동 컨트롤러. ROBOTIS 것이고, 베이스를 모는 액션 항이 import 한다 --
  # 없으면 cyclo_lab 을 import 하는 것만으로 태스크 등록이 죽는다(2026-08-24 실측).
  scripts/sim2real/bringup

  # 환경 코드
  source/cyclo_lab/setup.py
  source/cyclo_lab/pyproject.toml
  source/cyclo_lab/config
  source/cyclo_lab/cyclo_lab

  # 에셋 원본. 이 아래 다섯 줄이 로봇 하나, 진열대 하나, 책상 하나, 상자 하나,
  # 그리고 그 위에 서는 36 개 상품이다. 2 단계에서 배포용으로 다시 깔린다.
  source/cyclo_lab/data/robots/FFW/FFW_SG2.usd
  source/cyclo_lab/data/props/convstore/manifest.json
  source/cyclo_lab/data/props/convstore/layout.json
  source/cyclo_lab/data/props/convstore/fixtures/shelf_taskB
  source/cyclo_lab/data/props/convstore/taskB_products
  source/cyclo_lab/data/Table/Table.usd
  source/cyclo_lab/data/Crate/blue_box.usd
)

echo "[1/5] stage 를 비운다: $STAGE"
rm -rf "$STAGE" "$HERE/.assets"
mkdir -p "$STAGE"

echo "[2/5] $SRC 에서 추린다"
for p in "${KEEP[@]}"; do
  if [[ ! -e "$SRC/$p" ]]; then
    echo "  없음: $p" >&2
    exit 1
  fi
  mkdir -p "$STAGE/$(dirname "$p")"
  # tar 로 옮긴다. cp -r 은 심볼릭 링크와 권한에서 조용히 갈리고, 컨테이너가 만든
  # root 소유 파일(상품 텍스처가 그렇다)을 빠뜨린 적이 있다.
  tar -C "$SRC" -cf - --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' "$p" \
    | tar -C "$STAGE" -xf -
  # tar 의 --exclude 와 같은 조건으로 센다. 서브모듈의 .git 은 디렉토리가 아니라
  # 파일이라 '*/.git/*' 만으로는 걸러지지 않는다.
  a=$(find "$SRC/$p" -type f ! -path '*/.git' ! -path '*/.git/*' \
        ! -name '*.pyc' ! -path '*__pycache__*' | wc -l)
  b=$(find "$STAGE/$p" -type f | wc -l)
  if [[ "$a" != "$b" ]]; then
    echo "  파일 수가 다르다: $p  원본 $a  stage $b" >&2
    exit 1
  fi
  printf '  %-58s %s\n' "$p" "$(du -sh "$STAGE/$p" | cut -f1)"
done

echo "[3/5] 에셋을 배포용으로 다시 깐다"
# pxr 은 Isaac Sim 을 띄우지 않고도 쓸 수 있다 -- extscache 의 omni.usd.libs 를
# PYTHONPATH/LD_LIBRARY_PATH 에 얹으면 import 된다. 앱 기동 30~60 초를 아낀다.
# --user root 로 도는 이유: isaac-sim 이미지는 비-root 사용자로 시작해서 호스트가
# 소유한 /work 에 쓰지 못한다. 대신 컨테이너가 만든 파일은 root 소유로 남으므로,
# 같은 셸에서 바로 소유권을 되돌린다 -- root 소유 에셋은 나중에 다른 기계로 복사할 때
# 조용히 빠지고, 그렇게 상품 텍스처가 통째로 사라진 적이 있다.
docker run --rm --entrypoint bash --user root \
  -v "$HERE:/work" -e ACCEPT_EULA=Y \
  -e OWNER="$(id -u):$(id -g)" \
  "$BASE_IMAGE" -lc '
    set -e
    E=$(ls -d /isaac-sim/extscache/omni.usd.libs-* | head -1)
    export PYTHONPATH=$E:${PYTHONPATH:-}
    export LD_LIBRARY_PATH=$E/bin:$E/lib:${LD_LIBRARY_PATH:-}
    /isaac-sim/python.sh /work/reshape_assets.py /work/stage /work/.assets
    chown -R "$OWNER" /work/.assets
  '
# 원본 에셋 트리를 버리고 새 것을 그 자리에 놓는다. 코드는 data/ 를 패키지 옆에서
# 찾으므로(CYCLO_LAB_ASSETS_DATA_DIR) 자리는 그대로 두고 안을 바꾼다.
rm -rf "$STAGE/source/cyclo_lab/data"
mv "$HERE/.assets" "$STAGE/source/cyclo_lab/data"

echo "[4/5] 환경 코드의 경로 상수를 새 자리로"
python3 "$HERE/patch_paths.py" "$STAGE"
echo "  stage 전체 $(du -sh "$STAGE" | cut -f1)  (에셋 $(du -sh "$STAGE/source/cyclo_lab/data" | cut -f1))"

echo "[5/5] docker build -t $TAG"
docker build -t "$TAG" -f "$HERE/Dockerfile" "$HERE"
echo
echo "완료: $TAG"
echo "  .env 의 CHALLENGE_IMAGE 를 이 값으로 두고  docker compose up -d"
