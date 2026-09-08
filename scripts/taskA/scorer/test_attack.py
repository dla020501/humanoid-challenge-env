# Copyright 2025.
#
# **채점기를 공격한다.**  진짜 만점 로그를 비틀어 넣고, 한 일보다 많은 점수가 나오는지 본다.
#
# 왜 이 파일이 있나
#   채점기는 이제 우리 정답 주행이 아니라 **남의 로봇이 만든 로그**를 읽는다.  "우리 GT 로
#   21/21 이 나온다" 는 더 이상 충분한 검증이 아니다.  2026-09-08 에 열여섯 가지를 넣어 봤고,
#   **비율 100 % 를 공짜로 얻는 길이 다섯 개** 있었다:
#
#       토막 이름을 지운다         4 / 4  = 100 %      ← 항목 다섯이 아예 안 재졌다
#       전부 'place' 라고 한다   18 / 18 = 100 %
#       집기만 하고 끝            7 / 7  = 100 %
#       베이스를 순간이동          21 / 21 = 100 %      ← 주행 없이 도착
#       놓기 토막만 낸다          18 / 18 = 100 %
#
#   뿌리는 하나였다 -- **채점기가 「무엇을 잴지」를 로그더러 정하게 했다.**  그리고 그 로그는
#   채점받는 쪽이 만든다.
#
# 아래 기대값은 그 구멍을 막은 뒤의 것이다.  **이 파일이 깨지면 구멍이 다시 열린 것이다.**
#
# Run:  python3 scripts/taskA/scorer/test_attack.py

import copy
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import log_check as LC          # noqa: E402
import rubric_taskA as R        # noqa: E402
import score_from_log as SFL    # noqa: E402
import taska_score as T         # noqa: E402

DEMO = os.path.join(os.path.dirname(_HERE), "demos", "demo_06.npz")
if not os.path.isfile(DEMO):
    print("시연 파일이 없다: %s" % DEMO)
    raise SystemExit(1)

META, HEAD, A = T.load(DEMO)
SCENE = T.scene_of(META)
TH = {k: getattr(R, k) for k in T.THRESHOLD_KEYS}
FAIL = []


def attack(label, head=None, a=None, scene=None):
    """공격 하나를 넣고 (점수, 만점, 거부사유) 를 돌려준다.  거부면 점수가 None 이다."""
    head = copy.deepcopy(head if head is not None else HEAD)
    a = {k: np.array(v, copy=True) for k, v in (a if a is not None else A).items()}
    scene = scene if scene is not None else SCENE
    probs = LC.problems(a, head, scene)
    if probs:
        return None, None, probs[0]
    r = R.score(SFL.merge([SFL.measure_one(head, a, scene, TH)]))
    return r["total"], r["possible"], None


def want_score(label, total, possible=21.0, **kw):
    got, pos, why = attack(label, **kw)
    if why is not None:
        FAIL.append("%s: 채점 거부됐다(%s) -- %g/%g 이 나와야 한다" % (label, why[:50], total, possible))
    elif got != total or pos != possible:
        FAIL.append("%s: %s/%s 가 나왔는데 %g/%g 이어야 한다" % (label, got, pos, total, possible))


def want_reject(label, needle, **kw):
    got, _pos, why = attack(label, **kw)
    if why is None:
        FAIL.append("%s: 채점 거부돼야 하는데 %g 점이 나왔다" % (label, got))
    elif needle not in why:
        FAIL.append("%s: 거부는 됐는데 이유가 다르다 -- %r" % (label, why[:70]))


def mut(**over):
    a = {k: np.array(v, copy=True) for k, v in A.items()}
    a.update(over)
    return a


def nan_in(key):
    a = {k: np.array(v, copy=True) for k, v in A.items()}
    a[key] = a[key].astype(np.float64)
    a[key][...] = np.nan
    return a


# ── 0. 기준 ──────────────────────────────────────────────────────────────────────────
want_score("정직한 만점 판", 21.0)

# ── 1. 이름표로 채점 범위를 정하려는 공격 ─────────────────────────────────────────────
# **한 시도는 한 타임라인이다.**  이름표는 판정에 끼어들지 않는다.
want_score("토막 이름을 지운다", 21.0, head={**HEAD, "segment": "?"})
want_score("전부 'place' 라고 한다", 21.0, head={**HEAD, "segment": "place"})
want_score("토막 이름이 아예 없다", 21.0, head={k: v for k, v in HEAD.items() if k != "segment"})

# ── 2. 덜 하고 비율을 벌려는 공격 ─────────────────────────────────────────────────────
# **분모는 언제나 21 이다.**  덜 하면 비율이 나빠진다.
n = len(A["t"])
want_score("집기만 하고 끝낸다", 7.0, a={k: v[:int(n * 0.12)] for k, v in A.items()})
want_score("집기+주행만 낸다", 7.0, a={k: v[:int(n * 0.65)] for k, v in A.items()})

# ── 3. 값을 위조하는 공격 ────────────────────────────────────────────────────────────
# **충돌은 배열로 판정한다.**  머리말이 아니라고 해도 배열이 부딪혔다면 부딪힌 것이다.
got, pos, why = attack("머리말 충돌 위조",
                       head={**HEAD, "hit": {"hit": False}},
                       a=mut(hit_now=np.ones_like(A["hit_now"]),
                             hit_depth_mm=np.full_like(A["hit_depth_mm"], 99.0)))
if why is not None:
    FAIL.append("머리말 충돌 위조: 채점 거부됐다 -- 점수가 나와야 한다")
elif got >= 4.0:
    FAIL.append("머리말 충돌 위조: %g 점이 나왔다 -- 충돌을 인정해 4점 미만이어야 한다" % got)

# ── 4. 로그가 물리적으로 말이 안 되는 공격 -> 채점 거부 ───────────────────────────────
for _k in ("base_pos", "crate_pos", "grip_pos", "desk_pos", "hit_now", "crate_quat"):
    want_reject("%s 가 전부 NaN" % _k, "숫자가 아닌", a=nan_in(_k))
want_reject("시계가 전부 0", "앞으로 가지 않는", a=mut(t=np.zeros_like(A["t"])))
want_reject("시계가 거꾸로 간다", "앞으로 가지 않는", a=mut(t=A["t"][::-1].copy()))
_tel = {k: np.array(v, copy=True) for k, v in A.items()}
_tel["base_pos"][len(_tel["base_pos"]) // 2:] = _tel["base_pos"][0] + 5.0
want_reject("베이스를 순간이동시킨다", "순간이동", a=_tel)
_telc = {k: np.array(v, copy=True) for k, v in A.items()}
_telc["crate_pos"][len(_telc["crate_pos"]) // 2:] = _telc["crate_pos"][0] + 5.0
want_reject("바구니를 순간이동시킨다", "순간이동", a=_telc)
want_reject("쿼터니언을 정규화 안 함", "정규화", a=mut(crate_quat=A["crate_quat"] * 3.0))
want_reject("프레임이 하나뿐", "프레임이", a={k: v[:1] for k, v in A.items()})
want_reject("필수 값이 없다", "필요한 값이 없다",
            a={k: v for k, v in A.items() if k != "desk_pos"})
_far = {k: np.array(v, copy=True) for k, v in A.items()}
_far["base_pos"][:, 0] += 100.0
want_reject("매장 밖으로 나간다", "매장 밖", a=_far)

# ── 5. 시간 ──────────────────────────────────────────────────────────────────────────
# 간격이 일정하면 위생 검사는 통과한다 -- 그것은 **제한 시간**이 잡을 일이다.
got, pos, why = attack("시계를 100배 느리게", a=mut(t=A["t"] * 100.0))
if why is not None:
    FAIL.append("시계 100배: 위생 검사가 잡았다 -- 제한 시간이 잡아야 한다")
elif got is None or got >= 21.0:
    FAIL.append("시계 100배: %s 점이 나왔다 -- 제한 시간에 잘려 만점보다 낮아야 한다" % got)
if R.TIME_LIMIT_S != 600.0:
    FAIL.append("제한 시간이 %g 초다 -- 한 시도 10 분이므로 600 이어야 한다" % R.TIME_LIMIT_S)

# ── 6. 분모가 정말 고정인가 ──────────────────────────────────────────────────────────
for _lab, _a in (("집기만", {k: v[:int(n * 0.12)] for k, v in A.items()}),
                 ("절반만", {k: v[:n // 2] for k, v in A.items()})):
    _t, _p, _w = attack(_lab, a=_a)
    if _w is None and _p != 21.0:
        FAIL.append("%s: 만점이 %s 다 -- 언제나 21 이어야 한다" % (_lab, _p))

# ── 7. 정직한 판이 검사에 걸리지 않는가 ───────────────────────────────────────────────
# **문턱이 좁으면 여기가 먼저 깨진다.**  공격을 막느라 정상을 막으면 안 된다.
for _s in (0, 2, 6):
    _f = os.path.join(os.path.dirname(_HERE), "demos", "demo_%02d.npz" % _s)
    if not os.path.isfile(_f):
        continue
    _m, _h, _arr = T.load(_f)
    _p = LC.problems(_arr, _h, T.scene_of(_m))
    if _p:
        FAIL.append("정답 주행 seed %d 가 위생 검사에 걸렸다: %s" % (_s, _p[0][:70]))
    _r = R.score(SFL.merge([SFL.measure_one(_h, _arr, T.scene_of(_m), TH)]))
    if (_r["total"], _r["possible"]) != (21.0, 21.0):
        FAIL.append("정답 주행 seed %d 가 %g/%g 이다 -- 21/21 이어야 한다"
                    % (_s, _r["total"], _r["possible"]))

# ── 8. 도착 판정 (2026-09-09 결정) ───────────────────────────────────────────────────
# 구역은 **책상 중심** 원이고 반지름은 씬에서 계산한다 (`|목표 − 책상|`, 우리 씬 0.900 m).
# 멈춤도 놓기도 요구하지 않는다.


def _items(a=None, head=None, scene=None):
    a = {k: np.array(v, copy=True) for k, v in (a if a is not None else A).items()}
    head = copy.deepcopy(head if head is not None else HEAD)
    scene = scene if scene is not None else SCENE
    if LC.problems(a, head, scene):
        return None
    return R.score(SFL.merge([SFL.measure_one(head, a, scene, TH)]))["items"]


def want_item(label, key, want, **kw):
    it = _items(**kw)
    if it is None:
        FAIL.append("%s: 채점 거부됐다 -- 점수가 나와야 한다" % label)
    elif it[key]["got"] is not want:
        FAIL.append("%s: %s 가 %s 인데 %s 여야 한다 (%s)"
                    % (label, key, it[key]["got"], want, it[key]["why"][:60]))


# 안 멈추고 지나가며 놓는다 -- 예전에는 도착 실패였다
_dt = float(np.median(np.diff(A["t"])))
_jit = np.zeros_like(A["base_pos"]); _jit[1::2, 1] = 0.200 * _dt      # 200 mm/s 로 계속 흔든다
want_item("안 멈추고 놓는다", "arrived", True, a=mut(base_pos=A["base_pos"] + _jit))

# 책상 둘레 구역 밖에 선다.
#
# 로봇을 옮기는 대신 **씬의 책상을 옮긴다.**  주행 경로가 매장을 가로지르고 남쪽 통로에서
# y = -2.75 까지 내려가므로, 로봇을 어디로 밀어도 책상 옆을 스치거나 매장 밖으로 나간다.
# 책상을 매장 반대편 구석에 두면 경로 전체가 확실히 구역 밖이다.
_far_scene = copy.deepcopy(SCENE)
_far_scene["desk"]["pos"] = [1.0, 7.0, _far_scene["desk"]["pos"][2]]
want_item("책상 구역 밖에 선다", "arrived", False, scene=_far_scene)
want_item("구역 밖이면 들고도 볼 시점이 없다", "held", False, scene=_far_scene)

# 구역 안에 들어왔지만 놓기를 실패한다 -> **도착과 들고는 받는다** (2026-09-09 되돌림)
_nodrop = {k: np.array(v, copy=True) for k, v in A.items()}
# 바구니를 상판보다 30 cm 위로 -- 얹힌 적이 없다.  **손가락도 같이 올린다** (안 그러면
# 「들고 있다」까지 같이 깨져서 무엇을 시험하는지 흐려진다).
_nodrop["crate_pos"][:, 2] += 0.30
_nodrop["grip_pos"][:, :, 2] += 0.30
want_item("놓기를 실패해도 도착은 받는다", "arrived", True, a=_nodrop)
want_item("놓기를 실패해도 들고는 받는다", "held", True, a=_nodrop)
want_item("그래도 얹기는 실패", "placed", False, a=_nodrop)

# 바구니를 한 번도 안 들고 구역에 간다 (손가락을 멀리 둔다)
_never = {k: np.array(v, copy=True) for k, v in A.items()}
_never["grip_pos"] = np.tile(_never["crate_pos"][:, None, :]
                             + np.array([0.0, 0.0, 5.0], np.float32),
                             (1, A["grip_pos"].shape[1], 1)).astype(A["grip_pos"].dtype)
want_item("구역 안에서 한 번도 안 들었다", "held", False, a=_never)

# 구역 반지름이 씬에서 계산되고, **한계 안에 머무는가.**
#
# 반지름은 `|목표 − 책상|` 인데 씬이 책상을 멀리 두면 그만큼 커진다 -- 시험 삼아 4 m 옮겼더니
# 4.35 m 가 나왔고, 그러면 매장 절반이 「도착」이 된다.  그래서 위아래로 한계를 뒀다.
_wide = copy.deepcopy(SCENE)
_wide["desk"]["pos"] = [_wide["desk"]["pos"][0] + 4.0, _wide["desk"]["pos"][1],
                        _wide["desk"]["pos"][2]]
_m = SFL.measure_one(copy.deepcopy(HEAD), {k: np.array(v, copy=True) for k, v in A.items()},
                     _wide, TH)
if _m["arrive"]["zone_m"] > R.ARRIVE_ZONE_MAX_M + 1e-9:
    FAIL.append("책상을 4 m 옮겼더니 구역이 %.2f m 다 -- 한계 %.2f m 를 넘으면 안 된다"
                % (_m["arrive"]["zone_m"], R.ARRIVE_ZONE_MAX_M))
_tight = copy.deepcopy(SCENE)
_tight["desk"]["pos"] = [_tight["goal"]["xy"][0], _tight["goal"]["xy"][1],
                         _tight["desk"]["pos"][2]]
_m2 = SFL.measure_one(copy.deepcopy(HEAD), {k: np.array(v, copy=True) for k, v in A.items()},
                      _tight, TH)
if _m2["arrive"]["zone_m"] < R.ARRIVE_ZONE_MIN_M - 1e-9:
    FAIL.append("책상과 목표가 겹친 씬에서 구역이 %.2f m 다 -- 바닥 %.2f m 아래로 가면 안 된다"
                % (_m2["arrive"]["zone_m"], R.ARRIVE_ZONE_MIN_M))
# 우리 씬은 한계 사이에 편안히 들어와야 한다
_base = SFL.measure_one(copy.deepcopy(HEAD), {k: np.array(v, copy=True) for k, v in A.items()},
                        SCENE, TH)
if not (R.ARRIVE_ZONE_MIN_M < _base["arrive"]["zone_m"] < R.ARRIVE_ZONE_MAX_M):
    FAIL.append("우리 씬의 구역이 %.2f m 로 한계에 붙어 있다 (%.2f ~ %.2f)"
                % (_base["arrive"]["zone_m"], R.ARRIVE_ZONE_MIN_M, R.ARRIVE_ZONE_MAX_M))


if FAIL:
    print("실패 %d건" % len(FAIL))
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("공격 전부 막혔다 (정답 주행 3판은 그대로 21/21)")
