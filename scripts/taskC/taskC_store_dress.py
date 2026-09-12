# Copyright 2025.
#
# **기타 진열대(곤돌라 12 개)에 이 씨앗의 진열을 건다 -- 과제 C 판.**
#
# 과제 C 는 단독으로 돌아야 하므로 과제 A 모듈을 부르지 않는다. 같은 방식을 이 폴더 안에
# 둔다: 구워 둔 진열(`taskC/stores/store_vNN/*.usdc`)을 씨앗으로 하나 골라 곤돌라 프림의
# 참조만 갈아 끼운다. 진열대의 자리·크기·발자국은 씨앗과 무관하고, 선반에 선 상품만 바뀐다.
# 계산대·스캐너·빨간 띠·집는 상품은 이 파일이 건드리지 않는다.
#
# 진열기를 그때그때 돌리지 않고 구워 둔 것을 읽는 까닭은 재현성이다. 같은 씨앗·같은 코드라도
# 기계가 다르면 진열기의 부동소수점 가중치에서 난수 흐름이 갈려 결과가 달라진다(과제 A 실측).
# 구워 두면 어느 기계에서든 같은 그림이 선다.

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
STORES = os.path.join(_HERE, "stores")   # taskC/stores/
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


def store_seed_for(scene_seed):
    """장면 씨앗 -> 진열 씨앗. 우리 장면 씨앗은 3000 배수라 나머지 연산을 그대로 쓰면
    한쪽으로 쏠린다. 해시로 한 번 섞어 12 벌에 고르게 떨어지게 한다."""
    import random
    return random.Random("%s-store" % scene_seed).randrange(1000000)


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


