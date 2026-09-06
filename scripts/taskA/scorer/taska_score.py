# Copyright 2025.
#
# **시연 기록 한 판을 평가표대로 채점한다.**
#
#     python3 scripts/taskA/scorer/taska_score.py scripts/taskA/demos/demo_00.npz
#
# Isaac Sim 이 필요 없다. numpy 만 있으면 돈다 -- 채점이 보는 것은 전부 **자리**이지 힘이
# 아니기 때문이다. 과제 B 의 `taskb_score.py` 를 npz 하나로 돌리는 것과 같은 꼴이다.
#
# 과제 A 의 평가표는 **여섯 항목 21 점**이고, 시도 3 회를 합해 63 점이 최종 만점이다.
#
#     매장 가구와 부딪히지 않았는가          판 내내        4
#     바구니를 띄웠고 그때 그리퍼가 물었는가   한 번이라도     3
#     목적지에 도착해 멈췄는가               한 번이라도     3
#     그 시점에 로봇이 들고 있었는가          그 시점에       4
#     책상 상판에 얹었는가                   한 번이라도     3
#     손을 뗀 뒤 6 초 동안 잘 놓여 있었는가    손 뗀 뒤 6초    4
#
# **떨림은 채점 항목이 아니다.** 로봇이 덜덜거리며 가도 도착하면 점수는 같다.
#
# 이 파일이 하는 일은 시연 파일을 채점기가 아는 모양으로 바꿔 주는 것뿐이다.
#   * `score/*` 열여섯 갈래를 세 토막(집기·주행·놓기)으로 자르고
#   * 토막마다 `score_from_log.measure_one()` 을 부르고
#   * `merge()` 로 합쳐 `rubric_taskA.score()` 에 넣는다
# 판정식은 한 줄도 여기 없다. 문턱과 산식은 `rubric_taskA.py` 와 `score_from_log.py` 에 있다.
#
# 「쥐고 있나」를 힘이 아니라 자리로 보는 이유
#   힘으로 재려면 물리를 다시 돌려야 하는데, 긴 주행에서는 그 재계산이 원래 기록과 다르게
#   흘러가 바구니를 놓치는 일이 생긴다. 자리로 재면 기록만 있으면 된다. 믿을 만한지는
#   확인했다 -- 화면 7,041 장에서 힘으로 잰 답과 99.9 % 같았다 (어긋난 것 9 장).

import argparse
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import rubric_taskA as R          # noqa: E402
import score_from_log as SFL      # noqa: E402

THRESHOLD_KEYS = ("LIFT_OK_MM", "ARRIVE_ZONE_M", "STOP_MM_S", "CONTACT_N",
                  "SEAT_ON_MAX_MM", "OVERHANG_OK_MM", "TILT_OK_DEG",
                  "WATCH_S", "WATCH_TAIL_S", "DESK_OK_MM", "TIME_LIMIT_S")


def load(path):
    """시연 파일 하나 -> (meta, 토막별 (머리말, 배열사전)).

    토막은 `segment` 열이 가른다. 세 토막이 이어 붙어 있고 순서는 집기·주행·놓기다.
    """
    z = np.load(path, allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    if "scoring" not in meta:
        raise SystemExit(
            "이 시연 파일에는 채점용 데이터가 없다: %s\n"
            "`score/*` 갈래를 담은 판만 채점할 수 있다." % os.path.basename(path))
    seg = np.asarray(z["segment"], dtype=np.int64)
    names = meta["segment_names"]
    fields = meta["scoring"]["fields"]
    cols = {f: np.asarray(z["score/" + f]) for f in fields}
    z.close()

    parts = []
    for i, name in enumerate(names):
        m = seg == i
        n = int(m.sum())
        if n == 0:
            continue
        head = dict(meta["scoring"]["segments"][name])
        parts.append((head, {f: cols[f][m] for f in fields}))
    return meta, parts


def scene_of(meta):
    """채점기가 씬 파일에서 읽던 값. 시연 파일이 그대로 싣고 있다."""
    sc = meta["scoring"]["scene"]
    return {"meta": {"name": sc["name"], "seat": meta["seat"],
                     "corridor": sc.get("corridor")},
            "desk": sc["desk"], "goal": sc["goal"]}


def score_one(path, quiet=False):
    meta, parts = load(path)
    scene = scene_of(meta)
    th = {k: getattr(R, k) for k in THRESHOLD_KEYS}
    measured = [SFL.measure_one(h, a, scene, th) for h, a in parts]
    m = SFL.merge(measured)
    result = R.score(m)

    if not quiet:
        print("\n[채점] %s  --  seed %d, 좌석 %d, %d 프레임 (%.1f 초)"
              % (os.path.basename(path), meta["seed"], meta["seat"],
                 meta["frames"], meta["frames"] / meta["fps"]))
        print("       토막 %s"
              % ", ".join("%s(%d)" % (p["segment"], p["frames"]) for p in measured))
        print()
        print(R.render(result))
        for p in measured:
            for note in p.get("notes", []):
                print("  * %s: %s" % (p["segment"], note))
    return {"file": os.path.basename(path), "seed": meta["seed"], "seat": meta["seat"],
            "measured": m, "per_segment": measured, "score": result}


def main():
    ap = argparse.ArgumentParser(
        description="과제 A 의 시연 기록을 평가표대로 채점한다. Isaac Sim 이 필요 없다.")
    ap.add_argument("demo", nargs="+", help="scripts/taskA/demos/demo_NN.npz")
    ap.add_argument("--out", type=str, default=None, help="결과를 JSON 으로 저장")
    ap.add_argument("--quiet", action="store_true", help="표를 찍지 않는다")
    a = ap.parse_args()

    out = [score_one(p, quiet=a.quiet) for p in a.demo]

    if len(out) > 1:
        tot = sum(o["score"]["total"] for o in out)
        pos = sum(o["score"]["possible"] for o in out)
        print("\n════ %d 판 합계 %g / %g 점 ════" % (len(out), tot, pos))
        for o in out:
            print("  seed %-3d 좌석 %-3d %g / %g"
                  % (o["seed"], o["seat"], o["score"]["total"], o["score"]["possible"]))

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print("\n결과: %s" % a.out)


if __name__ == "__main__":
    main()
