#!/usr/bin/env bash
# 배포 이미지를 만든다.
#
#   ./build_image.sh /path/to/cstore-challenge [태그]
#
# 대회 환경 저장소에서 **과제 B 를 세우는 데 필요한 것만** 추려 docker/stage/ 에 놓고,
# 그 트리로 Dockerfile 을 빌드한다. 추리는 목록이 곧 "참가자에게 무엇을 주는가" 이므로
# 아래 KEEP 배열이 이 저장소에서 가장 중요한 열 몇 줄이다.
#
# 참가자는 이 스크립트를 쓸 일이 없다 — 이미지는 받아서 쓰는 것이다. 이것은 대회 측이
# 그 이미지를 어떻게 만드는지에 대한 기록이자, 다시 만들 수 있게 하는 수단이다.
set -euo pipefail

SRC="${1:-}"
TAG="${2:-ghcr.io/kairobahq/humanoid-challenge-env:latest}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE="$HERE/stage"

if [[ -z "$SRC" || ! -d "$SRC/source/cyclo_lab" ]]; then
  echo "사용법: $0 /path/to/cstore-challenge [태그]" >&2
  exit 1
fi
SRC="$(cd "$SRC" && pwd)"

# 이미지에 들어가는 것 전부. 경로는 대회 환경 저장소의 루트 기준.
KEEP=(
  # 라이선스 — README 의 고지가 가리키는 파일들
  LICENSE
  LICENSE-IsaacLab
  THIRD_PARTY_LICENSES.md

  # Isaac Lab (BSD-3-Clause, 원본 무수정)
  third_party/IsaacLab

  # 환경 코드. 데이터는 아래에서 따로 고른다
  source/cyclo_lab/setup.py
  source/cyclo_lab/pyproject.toml
  source/cyclo_lab/config
  source/cyclo_lab/cyclo_lab

  # 스워브 구동 컨트롤러. ROBOTIS 것이고, 베이스를 모는 액션 항이 import 한다 --
  # 없으면 cyclo_lab 을 import 하는 것만으로 태스크 등록이 죽는다(2026-08-24 실측).
  scripts/sim2real/bringup

  # 로봇 — FFW-SG2 의 USD (ROBOTIS 원본 무수정)
  source/cyclo_lab/data/robots

  # 과제 B 의 장면을 이루는 에셋. 이 네 줄이 진열대 하나, 책상 하나, 상자 하나,
  # 그리고 그 위에 서는 36 개 상품이다.
  source/cyclo_lab/data/props/convstore/manifest.json
  source/cyclo_lab/data/props/convstore/layout.json
  source/cyclo_lab/data/props/convstore/fixtures/shelf_taskB
  source/cyclo_lab/data/props/convstore/taskB_products
  # 그 36 개 상품의 **텍스처**. 상품 USD 가 여기를 절대경로로 참조한다 -- 빼면 진열대가
  # 통째로 무광 회색으로 뜬다(2026-08-24 실측: UsdToMdl 이 diffuse_texture 를 못 찾는다는
  # 오류 39 줄). 텍스처만 골라 낼 수도 있지만(142M/200M) 참조를 쪼개다 또 빠뜨리는 쪽이
  # 위험해서 폴더째 넣는다.
  source/cyclo_lab/data/our_scan_data
  source/cyclo_lab/data/props/convstore/products/pringles_taskB
  source/cyclo_lab/data/Table
  source/cyclo_lab/data/Crate
)

echo "[1/4] stage 를 비운다: $STAGE"
rm -rf "$STAGE"
mkdir -p "$STAGE"

echo "[2/4] $SRC 에서 추린다"
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
  echo "  $(printf '%-58s' "$p") $(du -sh "$STAGE/$p" | cut -f1)"
done

echo "[3/4] 옮겨진 것을 원본과 대조한다"
fail=0
for p in "${KEEP[@]}"; do
  # tar 의 --exclude 와 같은 조건으로 센다. 서브모듈의 .git 은 디렉토리가 아니라
  # 파일이라 '*/.git/*' 만으로는 걸러지지 않는다.
  a=$(find "$SRC/$p" -type f ! -path '*/.git' ! -path '*/.git/*' \
        ! -name '*.pyc' ! -path '*__pycache__*' | wc -l)
  b=$(find "$STAGE/$p" -type f | wc -l)
  if [[ "$a" != "$b" ]]; then
    echo "  파일 수가 다르다: $p  원본 $a  stage $b" >&2
    fail=1
  fi
done
[[ "$fail" == 0 ]] || exit 1
echo "  모두 일치. stage 전체 $(du -sh "$STAGE" | cut -f1)"

echo "[4/4] docker build -t $TAG"
docker build -t "$TAG" -f "$HERE/Dockerfile" "$HERE"
echo
echo "완료: $TAG"
echo "  .env 의 CHALLENGE_IMAGE 를 이 값으로 두고  docker compose up -d"
