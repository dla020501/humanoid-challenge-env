#!/usr/bin/env bash
# 대회 오버레이 아카이브를 만들고, 검증용으로 이미지도 굽는다. (주최측 전용)
#
#   ./build_image.sh /path/to/cstore-challenge [태그]
#
# 네 걸음이다.
#
#   1. 추린다   대회 환경 저장소에서 필요한 것만 docker/stage/ 로 옮긴다.
#               아래 KEEP 배열이 "참가자에게 무엇을 주는가" 의 전부다.
#   2. 손본다   상품 skin USD 의 텍스처 참조를 자기 폴더의 상대경로로 다시 쓴다
#               (reshape_assets.py). **원본 저장소는 건드리지 않는다** -- 고치는 것은
#               stage 안의 사본뿐이다.
#   3. 묶는다   stage 를 dist/challenge-overlay.tar.gz 로 만든다. **이것이 배포물이다**
#               -- GitHub Release 에 올리고 주소를 공지한다.
#   4. 굽는다   그 트리로 Dockerfile 을 빌드한다 -- 주최측 검증용.
#
# **완성된 이미지는 재배포하지 않는다.** Isaac Sim 컨테이너는 NVIDIA Isaac Sim
# Additional Software and Materials License 가 지배하고, 그 2.2 절이 Software 의 어떤
# 부분도 제3자에게 배포하는 것을 금지한다 (2026-08-25 확인). 그래서 NVIDIA 바탕
# 이미지는 참가자가 NVIDIA 레지스트리에서 직접 받아 본인이 동의하고(ACCEPT_EULA),
# 우리는 대회 쪽 코드·에셋 오버레이만 배포한다. 참가자 빌드는 run/setup.sh 가 한다 --
# 오버레이를 stage/ 에 풀고 같은 Dockerfile 을 굽는, 이 스크립트의 4 단계와 같은 일이다.
#
# 에셋은 **원본 경로 그대로** 들어간다. 예전에는 과제 B 최소 에셋만 추려 배포용
# 이름으로 재배치했지만(2026-08-25 이전), 지금의 과제 B 씬은 매장 전체(픽스처 16종,
# 진열 상품, 바닥)를 스폰하므로 convstore 트리가 통째로 필요하고, 그러면 경로 상수를
# 갈아 끼우는 patch 단계는 할 일이 없다. 코드가 원본 경로를 그대로 찾는다.
set -euo pipefail

SRC="${1:-}"
TAG="${2:-humanoid-challenge-env:latest}"
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
# 여기에 **없는** 것 중 설명이 필요한 것:
#   taskC_products/  452 MB. 과제 C 가 들어올 때 함께 들어온다.
#   our_scan_data/   과제 B 상품의 원본 스캔 잔재. 씬이 읽지 않는다.
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

  # 에셋 -- 과제 B(Unified-v0) 씬이 스폰하는 전부 (2026-08-25 cfg 전수 실측):
  # 로봇, 매장 픽스처 16종(+바구니·작업 진열대), 진열 상품, 과제 B 상품 36개.
  # 책상·상자는 데모 스크립트가 쓴다.
  source/cyclo_lab/data/robots/FFW/FFW_SG2.usd
  source/cyclo_lab/data/props/convstore/manifest.json
  source/cyclo_lab/data/props/convstore/layout.json
  source/cyclo_lab/data/props/convstore/fixtures
  source/cyclo_lab/data/props/convstore/products
  source/cyclo_lab/data/props/convstore/taskB_products
  source/cyclo_lab/data/Table/Table.usd
  source/cyclo_lab/data/Crate/blue_box.usd
)

echo "[1/4] stage 를 비운다: $STAGE"
rm -rf "$STAGE"
mkdir -p "$STAGE"

echo "[2/4] $SRC 에서 추려 손본다"
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

# 상품 skin USD 의 텍스처 참조를 상대경로로 다시 쓴다 (stage 안 사본만).
# pxr 은 Isaac Sim 을 띄우지 않고도 쓸 수 있다 -- extscache 의 omni.usd.libs 를
# PYTHONPATH/LD_LIBRARY_PATH 에 얹으면 import 된다. 앱 기동 30~60 초를 아낀다.
# --user root 로 도는 이유: isaac-sim 이미지는 비-root 사용자로 시작해서 호스트가
# 소유한 /work 에 쓰지 못한다. 컨테이너가 만든 root 소유 파일은 다른 기계로 복사할 때
# 조용히 빠진 적이 있으므로 같은 셸에서 소유권을 되돌린다.
docker run --rm --entrypoint bash --user root \
  -v "$HERE:/work" -e ACCEPT_EULA=Y \
  -e OWNER="$(id -u):$(id -g)" \
  "$BASE_IMAGE" -lc '
    set -e
    E=$(ls -d /isaac-sim/extscache/omni.usd.libs-* | head -1)
    export PYTHONPATH=$E:${PYTHONPATH:-}
    export LD_LIBRARY_PATH=$E/bin:$E/lib:${LD_LIBRARY_PATH:-}
    /isaac-sim/python.sh /work/reshape_assets.py /work/stage
    chown -R "$OWNER" /work/stage/source/cyclo_lab/data
  '
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

# 변환 부산물 -- 개발 머신 절대경로가 적힌 config.yaml, 캐시 해시, LFS 속성
find "$STAGE/source/cyclo_lab/data/props/convstore/taskB_products" \
  \( -name config.yaml -o -name .asset_hash -o -name .gitattributes \) -delete

# 에셋을 코드와 떼어 놓는다 -- 이미지 안 /workspace/assets. Dockerfile 이 그 자리로 옮기고,
# 코드가 보는 source/cyclo_lab/data 자리에는 심볼릭 링크를 건다.
mv "$STAGE/source/cyclo_lab/data" "$STAGE/assets"

echo "  stage 전체 $(du -sh "$STAGE" | cut -f1)"

echo "[3/4] 오버레이를 묶는다"
mkdir -p "$HERE/dist"
tar -C "$STAGE" -czf "$HERE/dist/challenge-overlay.tar.gz" .
echo "  $(du -sh "$HERE/dist/challenge-overlay.tar.gz" | cut -f1)  dist/challenge-overlay.tar.gz  <- Release 에 올릴 배포물"

echo "[4/4] docker build -t $TAG  (주최측 검증용)"
docker build -t "$TAG" -f "$HERE/Dockerfile" "$HERE"
echo
echo "완료: $TAG"
echo "  배포하는 것은 dist/challenge-overlay.tar.gz 뿐이다. 이미지는 밖에 내지 않는다."
