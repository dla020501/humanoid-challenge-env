"""배포용으로 다시 깐 에셋 트리를 환경 코드가 찾게 만든다.

`reshape_assets.py` 가 에셋을 옮기고 나면 cyclo_lab 안의 경로 상수가 옛 자리를 가리킨다.
이 스크립트가 그 상수들을 새 자리로 고친다. **원본 저장소는 건드리지 않는다** -- 고치는
대상은 docker/stage/ 안의 사본이고, 그래서 수집·평가 파이프라인이 쓰는 경로는 그대로다.

고치는 곳은 아래 PATCHES 가 전부다. 하나라도 못 찾으면 실패한다 -- 원본이 바뀌었는데
조용히 지나가면, 참가자는 텍스처 없는 진열대나 import 오류를 받게 된다.
"""

import os
import sys

STAGE = sys.argv[1]
PKG = f"{STAGE}/source/cyclo_lab/cyclo_lab"

# (파일, 찾을 것, 바꿀 것, 왜)
PATCHES = [
    (f"{PKG}/assets/object/taskB_products.py",
     '_PROPS = f"{_DATA}/props/convstore"',
     '_PROPS = f"{_DATA}/products"',
     "상품 뿌리"),

    (f"{PKG}/assets/object/taskB_products.py",
     'DIR = os.environ.get("CYCLO_TASKB_PRODUCT_DIR") or (\n'
     '    f"{_PROPS}/taskB_products" if os.path.isfile(f"{_PROPS}/taskB_products/manifest.json")\n'
     '    else f"{_PROPS}/taskC_products")',
     'DIR = os.environ.get("CYCLO_TASKB_PRODUCT_DIR") or _PROPS',
     "배포판에는 상품 집합이 하나뿐이라 고를 것이 없다"),

    (f"{PKG}/assets/object/taskB_products.py",
     '_ORIENTATION = os.path.join(DIR, "taskb_orientation.json")',
     '_ORIENTATION = os.path.join(DIR, "orientation.json")',
     "어느 면이 위인가"),

    (f"{PKG}/assets/object/taskB_restock.py",
     '_PROPS = f"{_DATA}/props/convstore"',
     '_PROPS = f"{_DATA}/store"',
     "매장 매니페스트 -- 상품 매니페스트와는 다른 파일이다"),

    (f"{PKG}/assets/object/taskB_restock.py",
     '_DISPLAY_YAW_PATH = f"{taskB_products.DIR}/taskb_display_yaw.json"',
     '_DISPLAY_YAW_PATH = f"{taskB_products.DIR}/display_yaw.json"',
     "진열 각도"),

    (f"{PKG}/assets/object/taskB_restock.py",
     'fp = os.path.join(taskB_products.DIR, "grasp_filter.json")',
     'fp = os.path.join(taskB_products.DIR, "shapes.json")',
     "상자냐 원통이냐 -- 상자 안 배치를 정한다"),

    (f"{PKG}/simulation_tasks/manager_based/manipulation/pick_place/convstore_store.py",
     'PROPS = f"{CYCLO_LAB_ASSETS_DATA_DIR}/props/convstore"',
     'PROPS = f"{CYCLO_LAB_ASSETS_DATA_DIR}/store"',
     "시뮬레이터가 읽는 매장 매니페스트"),

    # PROPS 가 매장 쪽을 가리키게 됐으니, 상품 USD 를 찾는 곳은 따로 말해 줘야 한다.
    # 매장 상품 35 종의 usd 값은 이 뿌리에서 어긋나지만 그 USD 들은 배포판에 없고
    # 과제 B 는 그것들을 스폰하지 않는다.
    (f"{PKG}/simulation_tasks/manager_based/manipulation/pick_place/convstore_store.py",
     'return f"{PROPS}/{entry[\'usd\']}"',
     'return f"{CYCLO_LAB_ASSETS_DATA_DIR}/products/{entry[\'usd\']}"',
     "상품 USD 의 뿌리"),

    (f"{PKG}/assets/object/taskB_shelf.py",
     'TASKB_SHELF_USD = f"{_DATA}/props/convstore/fixtures/shelf_taskB/shelf_taskB.usd"',
     'TASKB_SHELF_USD = f"{_DATA}/fixtures/shelf/shelf.usd"',
     "진열대"),

    (f"{PKG}/assets/object/taskB_table.py",
     'TABLE_USD = f"{_DATA}/Table/Table.usd"',
     'TABLE_USD = f"{_DATA}/fixtures/table/table.usd"',
     "책상"),

    (f"{PKG}/assets/object/taskB_table.py",
     'CRATE_USD = f"{_DATA}/Crate/blue_box.usd"',
     'CRATE_USD = f"{_DATA}/fixtures/crate/crate.usd"',
     "상자"),

    (f"{PKG}/assets/robots/FFW_SG2.py",
     'usd_path=f"{CYCLO_LAB_ASSETS_DATA_DIR}/robots/FFW/FFW_SG2.usd"',
     'usd_path=f"{CYCLO_LAB_ASSETS_DATA_DIR}/robot/ffw_sg2.usd"',
     "로봇"),

    # ---------------------------------------------------------------- 과제 A
    # 여기에 항목이 없는 것이 맞다. 과제 A 의 장면 정의 모듈(`taskA_*.py`)과 실측값 JSON 은
    # 이미지가 아니라 **이 저장소의 `scripts/taskA/`** 에 산다 -- `scripts/` 가 마운트라
    # `git pull` 만으로 갱신되고, 참가자가 코드를 바로 읽을 수 있기 때문이다.
    # 이미지가 과제 A 를 위해 품는 것은 매장 USD(184 MB) 하나뿐이고, 그것은 경로를 고칠
    # 것이 없다 -- `reshape_assets.copy_scene()` 이 원본 배치를 그대로 옮긴다.
]


def main():
    for path, old, new, why in PATCHES:
        if not os.path.isfile(path):
            raise SystemExit(f"없는 파일: {path}")
        text = open(path, encoding="utf-8").read()
        if text.count(old) != 1:
            raise SystemExit(
                f"{os.path.relpath(path, STAGE)} 에서 '{why}' 를 고칠 수 없다.\n"
                f"  찾은 횟수: {text.count(old)} (1 이어야 한다)\n"
                f"  찾던 것: {old!r}\n"
                f"원본이 바뀌었다. patch_paths.py 를 다시 맞춰라.")
        open(path, "w", encoding="utf-8").write(text.replace(old, new))
        print(f"  {os.path.relpath(path, STAGE):<64s} {why}")
    print(f"[paths]    {len(PATCHES)} 곳")


main()
