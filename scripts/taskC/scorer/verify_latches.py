"""판정기 전이 검증 — **기본은 FAIL, 조건이 다 차는 순간에만 PASS 로 뒤집히는가.**

    python verify_latches.py <trace.jsonl> <scene.json> <decode.json>

성공 판 하나로 확인한다. 매 틱 각 항목의 상태를 찍어보고 아래를 검사한다.

  ① 시작 상태가 PASS 인 항목이 없다 (기본은 실패다)
  ② 각 항목은 **한 번만** 뒤집힌다 (FAIL -> PASS, 되돌아오지 않는다)
  ③ 뒤집힌 그 틱에 **그 항목의 조건이 전부 성립**해 있다
  ④ 바로 앞 틱에는 조건 중 하나 이상이 성립하지 않았다 (그래서 그때까지 FAIL 이었다)

④ 가 핵심이다. 조건이 다 차기 전에 미리 켜져 있으면 채점이 무의미하다.
"""
from __future__ import annotations

import json
import sys

import numpy as np

import score_from_trace as SFT
from geometry import closest_dist
from taskc_scorer import UNAVAILABLE

ITEMS = ["sub1_1_grip", "sub1_2_lift", "sub2_1_aim", "sub2_2_decode", "sub3_place"]

# 헤드캠 영상은 기록 프레임(30Hz)을 30fps 로 인코딩한다 -> 영상 = 실시간(1배속).
#   영상 시각 = 프레임 번호 / VIDEO_FPS
VIDEO_FPS = 30.0


def snapshot(sc, target):
    p = sc.scores[target]
    return {
        "sub1_1_grip": p.grip.state(), "sub1_2_lift": p.lift.state(),
        "sub2_1_aim": p.aim.state(), "sub2_2_decode": p.decode.state(),
        "sub3_place": p.place.state(),
    }


def main(trace_path, scene_path, decode_path):
    tr = SFT.load_trace(trace_path)
    scene = json.load(open(scene_path, encoding="utf-8"))
    dec = json.load(open(decode_path, encoding="utf-8"))
    target = scene["products"][0]["slug"]
    specs = SFT.build_products(scene, dec)
    he = [float(v) for v in scene["products"][0]["he"]]
    cyl = bool(scene["products"][0].get("cyl"))

    # 채점기를 SFT 와 똑같이 세우되, 틱마다 상태를 들여다본다.
    state = {"i": 0}
    cur = lambda: tr[state["i"]]                                    # noqa: E731
    prow = lambda: [x for x in cur()["products"] if x["slug"] == target][0]   # noqa: E731
    for s in specs:
        s["get_pose"] = (lambda sl: (lambda: (
            [x for x in cur()["products"] if x["slug"] == sl][0]["pos"],
            [x for x in cur()["products"] if x["slug"] == sl][0]["quat"])))(s["slug"])
        s["get_lin_vel"] = (lambda sl: (lambda: [
            x for x in cur()["products"] if x["slug"] == sl][0]["vel"]))(s["slug"])

    from taskc_scorer import ScoreConfig, TaskCScorer
    cfg = ScoreConfig()
    ok = any(d.get("ok") for d in dec.get("decode", []))

    def load(_s):
        r = cur()
        return None if r.get("grip_q") is None else float(
            np.clip(SFT.STIFFNESS * (r["grip_cmd"] - r["grip_q"]),
                    -SFT.EFFORT_LIMIT, SFT.EFFORT_LIMIT))

    def grasped(sl):
        if sl != target:
            return False
        ld = load(sl)
        return None if ld is None else bool(cur()["grip_cmd"] > 0.1
                                            and abs(ld) >= cfg.grip_load_min_nm)

    table_z, band = SFT.measure_scene(scene)
    sc = TaskCScorer(specs, cfg, table_z=table_z, band_rect=band,
                     beam_origin_fn=lambda: np.asarray(cur()["beam"], dtype=float),
                     grasp_fn=grasped,
                     grip_closed_fn=lambda sl: (cur()["grip_cmd"] > 0.1) if sl == target else False,
                     gripper_load_fn=load,
                     gripper_pos_fn=lambda _s: cur().get("grip_q"),
                     decode_fn=lambda sl: (specs[0]["expected_code"]
                                           if (sl == target and ok) else None))

    def conds(i):
        """그 틱에 각 항목의 조건이 어떻게 서 있었는지 -- 사람이 읽을 수 있게."""
        state["i"] = i
        r = tr[i]
        pr = [x for x in r["products"] if x["slug"] == target][0]
        v = dict(shape="cylinder" if cyl else "box", pos=pr["pos"], quat=pr["quat"])
        if cyl:
            v.update(radius=max(he[0], he[1]), half_height=he[2], axis_local=(0, 0, 1))
        else:
            v.update(half_extents=tuple(he))
        d = closest_dist(r["beam"], v)
        ld = load(target)
        amin_z = float(pr["pos"][2]) - he[2]
        return dict(load_nm=None if ld is None else round(abs(ld), 1),
                    grasped=grasped(target),
                    lift_mm=round((amin_z - table_z) * 1000, 1),
                    dist_m=round(d, 3),
                    near=d <= cfg.aim_dist_m,
                    speed_mms=round(float(np.linalg.norm(pr["vel"])) * 1000, 1))

    prev = {k: False for k in ITEMS}
    flips, problems = {}, []
    # ① 시작 상태 -- PASS 인 항목이 하나라도 있으면 안 된다.
    #    UNAVAILABLE 은 「아직 관측 전」이라 점수를 주지 않는다 -- FAIL 과 같은 편이다.
    start = snapshot(sc, target)
    for k in ITEMS:
        if start[k] is True:
            problems.append(f"{k}: 시작부터 PASS 였다 (기본은 점수 없음이어야 한다)")

    for i in range(len(tr)):
        state["i"] = i
        sc.tick(float(tr[i]["t"]))
        now = snapshot(sc, target)
        for k in ITEMS:
            was, is_ = prev[k], now[k] is True
            if is_ and not was:
                if k in flips:
                    problems.append(f"{k}: 두 번 이상 뒤집혔다")
                flips[k] = dict(i=i, t=round(float(tr[i]["t"]), 2),
                                vt=round(i / VIDEO_FPS, 2),
                                at=conds(i), before=conds(max(i - 1, 0)))
            if was and not is_:
                problems.append(f"{k}: PASS 였다가 되돌아갔다 (t={tr[i]['t']:.2f})")
            prev[k] = is_
        if sc.stopped:
            break

    return dict(target=target, frames=len(tr), start=start,
                final=snapshot(sc, target), flips=flips, problems=problems,
                points=sc.scores[target].points(), stopped=sc.stopped)


def _fmt(r):
    L = [f"대상 {r['target']}  프레임 {r['frames']}  최종 {r['points']:.1f}점",
         f"영상 기준: {VIDEO_FPS:.0f}fps 인코딩, 총 {r['frames']/VIDEO_FPS:.1f}초 "
         f"(기록 30Hz -> 1배속, 실시간)"]
    L.append("")
    n_pass0 = sum(1 for k in ITEMS if r["start"][k] is True)
    L.append(f"① 시작 상태 — PASS 인 항목 {n_pass0}개 (0 이어야 한다)")
    for k in ITEMS:
        s = r["start"][k]
        tag = "PASS" if s is True else ("FAIL" if s is False else "미관측(점수 없음)")
        L.append(f"   {k:<16} {tag}")
    L.append("")
    L.append("② 뒤집힌 순간 — 조건이 그 틱에 처음으로 다 찼는가  ★영상 기준 초")
    for k in ITEMS:
        f = r["flips"].get(k)
        if not f:
            L.append(f"   {k:<16} 뒤집히지 않음 (최종 "
                     f"{r['final'][k] if r['final'][k] != True else 'PASS'})")
            continue
        a, b = f["at"], f["before"]
        L.append(f"   {k:<16} 영상 {f['vt']:>6.2f}초   (시뮬 t={f['t']}s, 프레임 {f['i']})")
        L.append(f"      뒤집힌 틱  부하 {a['load_nm']}N·m  쥠 {a['grasped']}  "
                 f"들림 {a['lift_mm']}mm  빔거리 {a['dist_m']}m(이내 {a['near']})  속도 {a['speed_mms']}mm/s")
        L.append(f"      직전 틱    부하 {b['load_nm']}N·m  쥠 {b['grasped']}  "
                 f"들림 {b['lift_mm']}mm  빔거리 {b['dist_m']}m(이내 {b['near']})  속도 {b['speed_mms']}mm/s")
    L.append("")
    if r["problems"]:
        L.append("③ 문제")
        for p in r["problems"]:
            L.append(f"   ! {p}")
    else:
        L.append("③ 문제 없음 — 전부 FAIL 에서 시작해 한 번씩만 뒤집혔고 되돌아가지 않았다")
    return "\n".join(L)


if __name__ == "__main__":
    print(_fmt(main(*sys.argv[1:])))
