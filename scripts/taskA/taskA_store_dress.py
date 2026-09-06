# Copyright 2025.
#
# **기타 진열대(곤돌라 12 개)에 이 seed 의 진열을 건다.**
#
# 평가표: *"진열대(목표 진열대 + 기타 진열대)에 진열되어 있는 상품은 랜덤 (진열대 자체의
# 배치는 달라지지 않음)"*. 목표 진열대는 `taskA_shelf_stock.py` 가, 곤돌라는 이 파일이 한다.
#
# **자리는 안 바뀌고 물건만 바뀐다.** 곤돌라의 위치·크기·발자국은 seed 와 무관하다. 바뀌는
# 것은 선반에 무엇이 서 있는가뿐이다. 그래서 충돌 판정이 보는 것은 seed 를 타지 않고,
# 정책이 보는 그림만 매번 달라진다.
#
# ----------------------------------------------------------------------------------
# 왜 진열기를 돌리지 않고 **구워 둔 것을 읽는가**
# ----------------------------------------------------------------------------------
# 원래 이 자리에는 진열기(`fixture_kit/live.py` 와 그 스토커들)를 돌려 매번 새로 채우는
# 코드가 있었다. 그것을 여기 옮기지 않은 이유는 크기가 아니라 **재현성**이다.
#
# 실측 2026-09-04 -- 같은 씨앗, 같은 코드, 같은 에셋(상품 라이브러리 160 개와 매장 USD 의
# md5 가 세 기계에서 동일)인데 결과가 달랐다:
#
#     씨앗 533391    클러스터에서 곤돌라 22 종 103 개    A 서버에서 17 종 105 개
#     씨앗 533392    클러스터에서 21 종  78 개          A 서버에서 22 종 118 개
#
# 같은 기계에서 두 번 돌리면 완전히 같았고, A 서버에서 수집 코드를 돌리면 A 서버 렌더와
# 같은 값이 나왔다 -- **기계가 원인이다.** 스토커가
# `rng.choices(..., weights=[f ** layer_bias ...])` 로 부동소수점 가중치를 쓰는데, CPU 가
# 다르면 `**` 의 마지막 자리가 갈리고 한 번 갈리면 이후 난수 흐름이 통째로 달라진다.
# 고칠 수 있는 종류의 차이가 아니다.
#
# 그런데 이 저장소의 README 는 참가자에게 이렇게 약속하고 있다:
#
#     "`--seed` 가 같으면 어디서 몇 번을 돌려도 같은 장면입니다."
#
# 진열기를 실어 보내면 그 약속이 곤돌라에서 깨진다. 그것도 **조용히** 깨진다 -- 두 장면 다
# 정상으로 열리고 로봇도 잘 달린다. 그래서 진열기를 보내지 않고, 미리 구운 결과를 보낸다.
# 파일을 읽는 데는 기계가 끼어들 자리가 없다.
#
# ----------------------------------------------------------------------------------
# 구운 것이 무엇인가
# ----------------------------------------------------------------------------------
#     stores/index.json          변주 목록
#     stores/store_vNN/*.usdc    유닛(곤돌라) 하나에 한 장
#     stores/store_vNN/index.json  어느 프림에 어느 파일을 걸지
#
# 유닛 파일은 상품 USD 를 **참조만** 한다 -- 메시를 품지 않아서 유닛 하나가 16 KB 남짓이고,
# 변주 한 벌이 195 KB, 12 벌 전부가 2.3 MB 다.
#
# **이 12 벌이 거는 상품 파일 25 개는 전부 배포 이미지에 이미 들어 있다** (2026-09-07 실측,
# `Task-A/eval_kit/bake_stores.py` 의 참조 검사). 그래서 이미지를 한 바이트도 바꾸지 않고
# 돈다. 이것이 중요한 이유: 참조가 하나라도 밖을 가리키면 USD 는 **오류 없이** 열리고 그
# 진열대만 텅 빈다. 조용히 실패하는 종류라 검사를 코드에 넣어 두었다.
#
# ----------------------------------------------------------------------------------
# 부르는 자리 -- `taskA_colliders.harden()` **앞**
# ----------------------------------------------------------------------------------
# 진열을 걸면 유닛 프림의 참조가 통째로 갈린다. harden 을 먼저 하면 콜라이더 설정이
# **이미 없어진 프림**에 붙고, 그러면 로봇이 진열대를 뚫고 지나가는데 발자국을 비교하는
# 충돌 판정은 그것을 알아채지 못한다. 순서가 load-bearing 이다.
#
# 이 파일은 대회 환경 저장소 `Task-A/sim/store_bake.py:load()` 를 옮긴 것이다.
# pxr 말고는 아무것도 import 하지 않는다.

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
STORES = os.path.join(_HERE, "stores")
STORE_ROOT = "/World/envs/env_0/Store"      # Isaac Lab 이 단일 환경에서 매장을 두는 자리
INDEX = "index.json"


def variants(stores=STORES):
    """구워진 변주 폴더 이름들. 없으면 빈 목록."""
    p = os.path.join(stores, INDEX)
    if not os.path.isfile(p):
        return []
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    return [v["dir"] for v in d.get("variants", [])]


def pick(store_seed, stores=STORES):
    """이 씨앗이 쓸 변주 폴더의 전체 경로. 구운 것이 없으면 None."""
    vs = variants(stores)
    if not vs:
        return None
    return os.path.join(stores, vs[int(store_seed) % len(vs)])


def dress(stage, store_seed, root=STORE_ROOT, stores=STORES, log=print):
    """곤돌라에 이 씨앗의 진열을 건다. 건 유닛 수를 돌려준다.

    구워 둔 것이 없으면 0 을 돌려주고 **씬은 매장 USD 가 실어 온 진열 그대로** 간다.
    그것도 정상으로 도는 장면이라 여기서 멈추지 않는다 -- 다만 조용히 넘어가지도 않는다.
    """
    from pxr import Sdf

    d = pick(store_seed, stores)
    if d is None:
        log("진열(기타): 구워 둔 것이 없다 — 매장 USD 의 기본 진열로 간다")
        return 0
    p = os.path.join(d, INDEX)
    if not os.path.isfile(p):
        log("진열(기타): 색인이 없다: %s" % p)
        return 0
    with open(p, encoding="utf-8") as fh:
        raw = json.load(fh)
    idx = raw["units"]
    unit_prim = raw.get("unit_prim", "/Unit")

    n, missing = 0, []
    with Sdf.ChangeBlock():
        for prim_path, name in idx.items():
            prim = stage.GetPrimAtPath(prim_path)
            if not prim or not prim.IsValid():
                missing.append(prim_path)
                continue
            f = os.path.join(d, name)
            if not os.path.isfile(f):
                missing.append(f)
                continue
            prim.GetReferences().SetReferences([Sdf.Reference(f, unit_prim)])
            n += 1
    log("진열(기타): 씨앗 %d -> %s, 곤돌라 %d/%d개"
        % (int(store_seed), os.path.basename(d), n, len(idx)))
    if missing:
        log("   !! 못 건 것 %d개: %s" % (len(missing), missing[0]))
    return n


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="어느 씨앗이 어느 진열을 쓰는지 본다. Isaac Sim 을 안 띄운다.")
    ap.add_argument("--store_seed", type=int, nargs="*", default=None)
    a = ap.parse_args()

    vs = variants()
    print("구워진 변주 %d벌: %s" % (len(vs), " ".join(vs)))
    if not vs:
        return
    seeds = a.store_seed
    if seeds is None:
        import taskA_scene_seed
        seeds = [taskA_scene_seed.spec(s)["store_seed"] for s in range(8)]
        print("\nseed 0~7 이 쓰는 진열:")
        for s in range(8):
            sp = taskA_scene_seed.spec(s)
            print("  seed %-3d  매장씨앗 %-7d  ->  %s"
                  % (s, sp["store_seed"], os.path.basename(pick(sp["store_seed"]))))
        return
    for s in seeds:
        print("  매장씨앗 %-7d -> %s" % (s, os.path.basename(pick(s))))


if __name__ == "__main__":
    main()
