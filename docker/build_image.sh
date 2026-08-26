#!/usr/bin/env bash
# 배포 이미지를 만든다.
#
#   ./build_image.sh /path/to/cstore-challenge [태그]
#
# 세 걸음이다.
#
#   1. 추린다   대회 환경 저장소에서 과제 A 와 B 에 필요한 것만 docker/stage/ 로 옮긴다.
#               아래 KEEP 배열이 "참가자에게 무엇을 주는가" 의 전부다 -- 단, 매장 에셋만은
#               예외로 넉넉히 옮겨 두고 2 단계에서 실제로 쓰이는 것만 골라 담는다. 그 이유는
#               KEEP 안에 적어 두었다.
#   2. 다시 깐다 에셋 트리를 배포용 이름으로 재배치하고(reshape_assets.py), 환경 코드의
#               경로 상수를 새 자리로 고친다(patch_paths.py). **원본 저장소는 건드리지
#               않는다** -- 고치는 것은 stage 안의 사본뿐이라, 수집·평가 파이프라인이
#               쓰는 경로는 그대로 남는다.
#   3. 굽는다   그 트리로 Dockerfile 을 빌드한다.
#
# 참가자는 이 스크립트를 쓸 일이 없다 -- 이미지는 받아서 쓰는 것이다. 이것은 대회 측이
# 그 이미지를 어떻게 만드는지에 대한 기록이자, 다시 만들 수 있게 하는 수단이다.
#
# `SKIP_BUILD=1` 을 주면 5 단계(굽기)를 건너뛰고 stage 만 만든다. 1~4 단계는 몇 분이고
# 굽기는 그보다 훨씬 오래 걸리므로, KEEP 을 고쳤을 때 "추려담기가 맞는가" 만 먼저 볼 때 쓴다.
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
# 여기에 **없는** 것 중 설명이 필요한 셋:
#   taskC_products/         과제 C 의 상품 452 MB. 과제 C 의 장면이 들어올 때 함께 온다.
#                           매장 정의(store/manifest.json)가 이름으로 언급하기는 하지만,
#                           과제 A 의 매장 USD 는 자기 상품을 스스로 물고 있어서 필요 없다.
#   our_scan_data/          상품 36 개가 taskB_products/ 와 md5 단위로 겹치는 사본이다
#                           (2026-08-25 확인). 옛날에는 이것도 넣어야 상품에 색이 입었는데,
#                           skin USD 가 텍스처를 그쪽 절대경로로 물고 있었기 때문이다.
#                           reshape_assets.py 가 그 경로를 상대경로로 다시 쓰므로 이제
#                           사본 한 벌이면 된다. 200 MB 가 그대로 빠진다.
#   FFW_SH5 / OMY USD       아무 과제도 쓰지 않는 로봇이다. 93 MB.
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

  # 에셋 원본. 로봇 하나, 집기 한 벌, 책상 하나, 상자 하나, 그리고 진열대에 서는 36 개
  # 상품이다. 2 단계에서 배포용으로 다시 깔린다.
  #
  # `fixtures/` 는 2026-08-25 에 `fixtures/shelf_taskB` 에서 통째로 넓혔다 -- 매장 USD 가
  # 쇼케이스·쓰레기통·계산대 같은 맨 집기를 여기서 참조하기 때문이다(과제 A). 넓혀도
  # 이미지가 48 MB 커지지는 않는다: reshape 가 매장 USD 에서 실제로 도달하는 것만 담는다.
  source/cyclo_lab/data/robots/FFW/FFW_SG2.usd
  source/cyclo_lab/data/props/convstore/manifest.json
  source/cyclo_lab/data/props/convstore/layout.json
  source/cyclo_lab/data/props/convstore/fixtures
  source/cyclo_lab/data/props/convstore/taskB_products
  source/cyclo_lab/data/Table/Table.usd
  source/cyclo_lab/data/Crate/blue_box.usd

  # 과제 A -- 매장 전체. 과제 B 가 진열대 하나 앞에서 벌어지는 것과 달리 과제 A 는 매장을
  # 가로지르므로 편의점이 통째로 필요하다.
  #
  # 이 아래는 **stage 로 옮기는 것**이고 이미지에 들어가는 것과 같지 않다. 위의 다른 항목들과
  # 다른 점이 여기 있다: `store_scene.usd` 는 참조 94 개와 텍스처 180 장을 물고 있는데 그
  # 목록은 사람이 손으로 적을 것이 아니다(적으면 반드시 어긋난다). 그래서 여기서는 넉넉히
  # 옮기고, `reshape_assets.py` 가 USD 를 열어 **실제로 도달하는 파일만** 골라 담는다.
  # 실측 2026-08-25: fixture_kit 에서 stage 로 347 MB 를 옮겨, 그중 이미지에 들어가는 것은
  # 191 MB (파일 274 개)다. 나머지는 4 단계 뒤 stage 에서 통째로 버린다.
  #
  # 좌석 실측값과 목적지도 여기 들어간다. 둘 다 참가자 데모가 장면을 세우는 데 쓴다.
  # `out/scenes` 가 아니라 `out` 통째다. 2026-08-25 에 scenes 만 넣었다가 곤돌라의
  # **가격표 그림 24 장**(`shelf_random_kit/out/price_pops/`)이 조용히 빠졌다 -- 씬은
  # 열리고 진열대도 서는데 가격표만 회색이 된다. 어느 킷이 out/ 어디에 무엇을 두는지는
  # 킷마다 다르므로, 고르는 일은 사람이 하지 말고 reshape 에게 맡긴다.
  fixture_kit/out/store_scene.usd
  fixture_kit/eatin_kit/assets
  fixture_kit/eatin_kit/out
  fixture_kit/freezer_kit/assets
  fixture_kit/freezer_kit/out
  fixture_kit/fridge_random_kit/assets
  fixture_kit/fridge_random_kit/out
  fixture_kit/liquor_shelf_kit/assets
  fixture_kit/liquor_shelf_kit/out
  fixture_kit/shelf_random_kit/assets
  fixture_kit/shelf_random_kit/out
  source/cyclo_lab/data/props/convstore/eatin_measured.json
  source/cyclo_lab/data/props/convstore/destinations.json
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

# 에셋 저작자 표시. **원본 저장소에서 오지 않는 유일한 파일이다.**
#
# 옆의 THIRD_PARTY_LICENSES.md 는 원본이 코드에 대해 쓰는 파일이라 KEEP 이 그대로 옮겨
# 온다. 그런데 이미지에 함께 실리는 3D 에셋 중에는 재배포에 저작자 표시가 따라가야 하는
# 것이 있고 -- 시식 코너 스툴이 CC BY 4.0 이다 -- 그 목록은 이 이미지가 무엇을 담기로
# 했느냐에 따라 달라진다(과제가 늘면 에셋도 는다). 원본에는 그 사정이 없으므로 여기서 만든다.
#
# README 의 라이선스 표에만 적어 두면 이미지만 받은 사람에게는 표시가 닿지 않는다.
cp "$HERE/NOTICE_ASSETS.md" "$STAGE/NOTICE_ASSETS.md"
printf '  %-58s %s\n' "NOTICE_ASSETS.md (이 레포에서)" "$(du -sh "$STAGE/NOTICE_ASSETS.md" | cut -f1)"

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
# fixture_kit 은 **원료**였다. reshape 가 매장 USD 에서 실제로 도달하는 것만 data/store/scene
# 으로 담았으므로 stage 에 남은 원본은 버린다 -- Dockerfile 이 `COPY stage/` 한 줄로 통째로
# 퍼 담기 때문에, 여기서 지우지 않으면 쓰이지 않는 347 MB 가 이미지에 그대로 들어간다.
rm -rf "$STAGE/fixture_kit"

echo "[4/5] 환경 코드의 경로 상수를 새 자리로"
python3 "$HERE/patch_paths.py" "$STAGE"
echo "  stage 전체 $(du -sh "$STAGE" | cut -f1)  (에셋 $(du -sh "$STAGE/source/cyclo_lab/data" | cut -f1))"

# ---------------------------------------------------------------- 걷어내기
# 참가자에게 안 나가는 것. FFW-SG2 와 대회 매장 환경만 남긴다 (2026-08-26 운영자 결정).
PKG="source/cyclo_lab/cyclo_lab"
PRUNE=(
  # 대회 무관 ROBOTIS 상류 태스크 (OMY 4종, K1 보행·모션 모방). simulation_tasks 는
  # 디렉토리 탐색(import_packages)으로 등록하므로 통째로 빼도 import 가 깨지지 않는다.
  $PKG/simulation_tasks/manager_based/locomotion
  $PKG/simulation_tasks/manager_based/mimic
  $PKG/simulation_tasks/manager_based/manipulation/cabinet
  $PKG/simulation_tasks/manager_based/manipulation/lift
  $PKG/simulation_tasks/manager_based/manipulation/reach
  $PKG/simulation_tasks/manager_based/manipulation/stack
  # 실기(sim2real) 태스크. __init__ 두 개는 남긴다 -- cyclo_lab/__init__ 이 이 패키지를
  # 명시 import 하고, 패키지 자체는 디렉토리 탐색이라 비어 있어도 된다.
  $PKG/real_world_tasks/manager_based/FFW_SG2
  $PKG/real_world_tasks/manager_based/OMY
  # 위 태스크들만 쓰던 물체 cfg
  $PKG/assets/object/{background_cube,brush_ring,plastic_basket,plastic_basket2,plastic_bottle,pliers_ring,robotis_aiworker_table,robotis_net_table,robotis_omy_table,scissors_ring,screw_driver_ring,silicone_tube_ring,tooth_brush}.py
  # 주최측 내부 도구 (시연 수집·파지 계획·설정 내보내기)
  $PKG/utils/graspgen_grasps.py
  $PKG/utils/export_git_state.py
  $PKG/utils/export_sim2real_cfg.py
  # 과제 B 판정기 — 채점표·임계값. cstore-challenge 4bd62ea 가 taskb_env_cfg 의 import 를
  # 선택적으로 바꿔(없으면 taskb_track 텀 생략) 이제 뺄 수 있다. pick_plan 은 taskb_events 만 썼다.
  $PKG/simulation_tasks/manager_based/manipulation/pick_place/mdp/taskb_judge.py
  $PKG/simulation_tasks/manager_based/manipulation/pick_place/mdp/taskb_events.py
  $PKG/simulation_tasks/manager_based/manipulation/pick_place/mdp/taskb_speed.py
  $PKG/utils/pick_plan.py
  # FFW-SG2 외 로봇 cfg. 4bd62ea 가 robots/__init__ import 를 선택적으로 바꿨다. USD 는 이미 없음.
  $PKG/assets/robots/OMY.py
  $PKG/assets/robots/FFW_SH5.py
  $PKG/assets/robots/K1_rev1.py
)
for p in "${PRUNE[@]}"; do
  if [[ ! -e "$STAGE/$p" ]]; then
    echo "  걷어낼 것이 없다 (원본이 바뀌었다): $p" >&2
    exit 1
  fi
  rm -rf "$STAGE/$p"
done
echo "  걷어냄: ${#PRUNE[@]} 항목"

# 에셋을 코드와 떼어 놓는다 -- 이미지 안 /workspace/assets. Dockerfile 이 그 자리로 옮기고,
# 코드가 보는 source/cyclo_lab/data 자리에는 심볼릭 링크를 건다.
mv "$STAGE/source/cyclo_lab/data" "$STAGE/assets"


if [[ -n "${SKIP_BUILD:-}" ]]; then
  echo "[5/5] SKIP_BUILD 가 설정돼 굽지 않는다. stage 만 만들어 두었다: $STAGE"
  exit 0
fi

echo "[5/5] docker build -t $TAG"
docker build -t "$TAG" -f "$HERE/Dockerfile" "$HERE"
echo
echo "완료: $TAG"
echo "  .env 의 CHALLENGE_IMAGE 를 이 값으로 두고  docker compose up -d"
