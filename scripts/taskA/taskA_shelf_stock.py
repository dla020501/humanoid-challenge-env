# Copyright 2025.
#
# **목표 진열대에 이 seed 의 상품을 세운다.**
#
# 평가표: *"진열대(목표 진열대 + 기타 진열대)에 진열되어 있는 상품은 랜덤 (진열대 자체의
# 배치는 달라지지 않음)"*. 곤돌라는 `taskA_store_dress.py` 가, 목표 진열대는 이 파일이 한다.
#
# 이것이 없으면 **목표 진열대가 텅 빈 채로 렌더된다.** 매장 USD 는 곤돌라·냉장고 진열은
# 실어 오지만 목표 진열대(`Fix_shelf_taskB`)는 비워 두기 때문이다 -- 그 진열대는 과제 B 가
# 채우는 대상이고, 과제 A 에서는 도착점의 표지다.
#
# 여기 새로 쓴 산식은 없다
#   과제 B 의 과제 자체가 이 진열대를 채우는 것이라 진열 코드가 이미 있고 이미 씨앗을
#   받는다. `taskB_restock.stock(board_tops, front_x, seed)` 가 채워진 칸마다
#   (상품, 자리, 층, 칸) 을 돌려주고, `layout(seed)` 가 어느 상품이 어느 열에 서고 앞줄 어느
#   세 칸을 비울지 정한다. **이 파일은 좌표계 변환뿐이다.**
#
# 놓치면 조용히 틀어지는 것 둘
#
#   1. 좌표계. 과제 B 는 로봇이 원점에 있고 진열대 앞면이 x = 0.47, y 중심이 0 인 세계에서
#      돈다. 이 매장은 같은 에셋을 앞면 x = 0.9134, 중심 y = 2.60 에 둔다. 둘 다 코드에
#      적지 않고 `store_fixtures.json` 에서 읽는다 -- 매장을 다시 구우면 진열대가 움직이고
#      상품이 따라간다.
#
#   2. 자세. `convstore_store.product_cfg` 의 `rot` 기본값은 **항등**인데, 항등은 "똑바로"
#      가 아니라 "그 상품 USD 가 어쩌다 저작된 대로" 다. 대회 환경 저장소의 CLAUDE.md 가
#      이것을 네 군데에서 빠뜨린 기록을 갖고 있고, 그중 하나가 과제 B 의 시연을 쓰는
#      스크립트였다 -- 녹화된 장면은 전부 진열이 틀어져 있었고 검사용 화면만 옳았다.
#      여기서는 모든 스폰이 `rot=taskB_restock.stock_orientation(name)[1]` 을 넘긴다.
#
# 프림 이름은 **대문자 그대로**다 (`{ENV_REGEX_NS}/L0_S00`). `setattr` 하는 속성 이름만
# 소문자이고, 프림 경로는 `product_cfg` 가 원래 대소문자를 쓴다. 씬 파일에 상품 자리를 적을
# 때 소문자로 찾으면 21 개를 하나도 못 찾는다 -- 그렇게 짰다가 관문에서 잡힌 적이 있다.
#
# 상품은 중력이 켜진 **강체**다. 과제 B 가 스폰하는 방식 그대로이고, 기본 씨앗에서 21 개가
# 선반 위에 내려앉는다.
#
# `stock()` 과 `gaps()` 는 **순수 산술이라 Isaac Sim 없이 돈다.** `task_a_demo.py --check`
# 가 시뮬레이터를 안 띄우고 1 초에 진열을 찍을 수 있는 것이 그 덕이다.
#
# 이 파일은 대회 환경 저장소 `Task-A/sim/shelf_stock.py` 에서 옮긴 것이다. 고친 것은
# **읽는 자리 둘뿐**이다 -- 배포 이미지에는 `Task-A/` 가 없고 과제 B 모듈은 이미지 안에,
# 진열대 좌표는 이 파일 옆에 있다.

import importlib.util as _ilu
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_FIXTURES = os.path.join(_HERE, "store_fixtures.json")

# 과제 B 모듈이 사는 곳. `taskA_layout.py` 와 같은 방식으로 찾는다.
_CYCLOLAB = os.environ.get("CYCLOLAB_PATH", "/workspace/cyclo_lab")
_OBJ = f"{_CYCLOLAB}/source/cyclo_lab/cyclo_lab/assets/object"

SHELF_NAME = "Fix_shelf_taskB"


def _load(name, filename):
    """**이미지 안** 과제 B 모듈을 경로로 읽는다.

    `import cyclo_lab...` 로 가면 패키지 __init__ 사슬이 isaaclab 을 끌고 들어오고,
    isaaclab 이 SimulationApp 보다 먼저 import 되면 Isaac Sim 이 아예 뜨지 않는다.
    `taskA_layout.py` 와 `taskB_table.py` 가 쓰는 것과 같은 방법이다.
    """
    path = os.path.join(_OBJ, filename)
    if not os.path.isfile(path):
        raise SystemExit(
            "과제 B 모듈을 찾지 못했다: %s\n"
            "CYCLOLAB_PATH 를 확인하라 (현재 %r). 컨테이너 안에서는 "
            "/workspace/cyclo_lab 이다." % (path, _CYCLOLAB))
    spec = _ilu.spec_from_file_location(name, path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def shelf_frame(fixtures=_FIXTURES):
    """(앞면 x, 중심 y). 매장에서 잰 값을 읽는다 -- 코드에 적지 않는다."""
    with open(fixtures, encoding="utf-8") as fh:
        d = json.load(fh)["fixtures"]
    f = next(x for x in d if x["name"] == SHELF_NAME)
    x0, y0, _x1, y1 = f["bbox"][:4]
    return float(x0), float((y0 + y1) / 2.0)


def stock(seed, fixtures=_FIXTURES):
    """[(프림 이름, 상품, (x, y, z), 쿼터니언)] -- 이 씨앗이 채우는 칸 전부.

    순수 산술이다. Isaac Sim 없이 돈다.
    """
    restock = _load("_taskA_taskB_restock", "taskB_restock.py")
    shelf = _load("_taskA_taskB_shelf", "taskB_shelf.py")
    front_x, y_centre = shelf_frame(fixtures)
    out = []
    for name, pos, layer, slot in restock.stock(shelf.BOARD_TOPS, front_x, seed=int(seed)):
        out.append(("L%d_S%02d" % (layer, slot), name,
                    (float(pos[0]), float(pos[1]) + y_centre, float(pos[2])),
                    tuple(restock.stock_orientation(name)[1])))
    return out


def gaps(seed):
    """[(층, 칸)] -- 비워 둔 자리. 언제나 앞줄이다 (과제 B 의 규칙)."""
    restock = _load("_taskA_taskB_restock", "taskB_restock.py")
    _cols, empty = restock.layout(int(seed))
    return [(int(a), int(b)) for a, b in empty]


def attach(cfg, seed, fixtures=_FIXTURES, log=print):
    """상품마다 `RigidObjectCfg` 를 `cfg` 에 단다. 단 개수를 돌려준다.

    `InteractiveSceneCfg.__post_init__` 에서 부른다. `InteractiveScene` 이 `cfg.__dict__` 를
    훑으므로 `setattr` 은 필드로 선언한 것과 같다 -- 과제 B 도 같은 방식이다.

    `convstore_store` 를 모듈 위가 아니라 여기서 import 하는 이유: 그것이 isaaclab 과 pxr 을
    끌고 들어오는데, 이 모듈은 앱을 띄우기 **전에도** 읽을 수 있어야 한다.
    """
    from cyclo_lab.simulation_tasks.manager_based.manipulation.pick_place import convstore_store

    items = stock(seed, fixtures)
    for prim, name, pos, quat in items:
        setattr(cfg, prim.lower(), convstore_store.product_cfg(prim, name, pos, rot=quat))
    if log:
        log("진열(목표): 씨앗 %d, 상품 %d개, 빈 칸 %s" % (seed, len(items), gaps(seed)))
    return len(items)


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="이 씨앗이 목표 진열대를 어떻게 채우는지 본다. Isaac Sim 을 안 띄운다.")
    ap.add_argument("--shelf_seed", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0, help="장면 seed (진열대씨앗을 여기서 뽑는다)")
    a = ap.parse_args()

    seed = a.shelf_seed
    if seed is None:
        import taskA_scene_seed
        seed = taskA_scene_seed.spec(a.seed)["shelf_seed"]
        print("장면 seed %d -> 진열대씨앗 %d" % (a.seed, seed))
    fx, fy = shelf_frame()
    print("목표 진열대 앞면 x %.4f, 중심 y %.4f" % (fx, fy))
    items = stock(seed)
    print("상품 %d개, 빈 칸 %s" % (len(items), gaps(seed)))
    for prim, name, pos, _q in items:
        print("  %-8s %-28s (%+.3f, %+.3f, %.3f)" % (prim, name, *pos))


if __name__ == "__main__":
    main()
