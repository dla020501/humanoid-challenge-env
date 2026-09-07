# Copyright 2025.
#
# `rubric_taskA.py` 단위 시험.  Isaac 도 프레임워크도 필요 없다 -- 몇 초에 돈다.
#
# 여기 있는 사례는 지어낸 것이 아니라 **기록에 남은 실패 모양**이다.  각 사례 위의 주석이
# 그것이 어디서 왔는지 적는다.  새 문턱을 넣거나 항목을 고칠 때 **이 파일이 먼저 깨져야
# 한다.**
#
# Run:
#   python3 scripts/taskA/scorer/test_rubric_taskA.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rubric_taskA as R  # noqa: E402

FAIL = []


def check(name, got, want):
    if got != want:
        FAIL.append(f"{name}: {got!r} 이 나왔는데 {want!r} 이어야 한다")


def near(name, got, want, tol=0.51):
    if got is None or abs(got - want) > tol:
        FAIL.append(f"{name}: {got!r} 이 나왔는데 {want!r} (±{tol}) 이어야 한다")


def m(**kw):
    """다 통과하는 판을 만들고, 넘긴 열쇠만 덮어쓴다."""
    base = {
        "ended": "ok",
        "elapsed_s": 435.0,
        "lift": {"peak_mm": 86.7, "gripped": True},
        "arrive": {"stopped_ever": True, "reached": True,
                   "nearest_edge_mm": 0.0, "held": True},
        "furniture": {"hit": False, "worst_mm": 0.0, "what": None, "part": None, "frames": 0},
        "place": {"reached_desk": True, "seat_mm": 1.5, "overhang_mm": 12.0, "at_s": 79.0,
                  "tilt_deg": 0.2, "seated_any": True, "upright_any": True},
        "watch": {"opened": True, "seat_mm": 1.5, "overhang_mm": 12.0,
                  "tilt_deg": 0.2, "tail_speed_mm_s": 0.3, "window_s": 6.0},
        "desk": {"worst_mm": 0.004},
    }
    for k, v in kw.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = {**base[k], **v}
        else:
            base[k] = v
    return base


def got(res, key):
    return res["items"][key]["got"]


# ── 배점이 시트 그대로인가 ────────────────────────────────────────────────────────────
# 시트의 「총 합 17」은 오타이고 21 이 맞다 (사용자 확인 2026-09-02).
check("항목 수", len(R.ITEMS), 6)
# **떨림이 채점 항목으로 들어오면 여기서 깨진다** (사용자 지시 2026-09-02).
# 거르는 자리는 채점기가 아니라 넘길 편을 고르는 단계다.
for _k in R.ITEMS:
    if "trem" in _k or "떨림" in R.LABEL[_k] or "swing" in _k:
        FAIL.append(f"떨림이 채점 항목에 들어왔다: {_k}")
check("떨림 문턱이 없다", any("TREMOR" in n or "SWING" in n for n in dir(R)), False)
check("배점 합", sum(R.POINTS.values()), 21.0)
check("최종 만점", sum(R.POINTS.values()) * R.ATTEMPTS, 63.0)
for k, p in (("no_hit", 4.0), ("picked", 3.0), ("arrived", 3.0),
             ("held", 4.0), ("placed", 3.0), ("stayed", 4.0)):
    check(f"{k} 배점", R.POINTS[k], p)

# ── 다 통과하는 판 ───────────────────────────────────────────────────────────────────
r = R.score(m())
check("만점 판 총점", r["total"], 21.0)
check("만점 판 분모", r["possible"], 21.0)
check("만점 판 못 잰 항목", r["unscored"], [])

# ── Sub 1# 은 **한 항목**이다 -- 둘 중 하나만 어긋나도 3점이 통째로 날아간다 ────────────
# 30 mm 를 못 넘긴 경우.  실측: 탁자 위에서 밀려 끌려간 편이 이 모양이었다.
check("덜 떠오름", got(R.score(m(lift={"peak_mm": 28.0})), "picked"), False)
# 떠오르긴 했는데 그리퍼가 아니라 딴 것이 받친 경우.  집게에 맞아 튕겨 오른 바구니도 30 mm 는 뜬다.
check("떠올랐으나 안 물음",
      got(R.score(m(lift={"peak_mm": 120.0, "gripped": False})), "picked"), False)
check("떠올랐으나 안 물음은 0점",
      R.score(m(lift={"peak_mm": 120.0, "gripped": False}))["items"]["picked"]["points"], 0.0)
# 높이는 읽었는데 접촉을 못 읽은 경우는 **0점이 아니라 분모에서 빠진다**
r = R.score(m(lift={"peak_mm": 120.0, "gripped": None}))
check("접촉 못 읽음 = None", got(r, "picked"), None)
check("접촉 못 읽으면 분모에서 빠짐", r["possible"], 18.0)

# ── Sub 2# 도착 -- 발자국이 구역에 걸치는가 ────────────────────────────────────────────
# 실측 2026-09-02, seed 0 GT: 3,102 프레임 내내 안 멈춘 것으로 나왔던 그 로그.
# (원인은 보고된 속도의 +39 mm/s 바이어스였고 `score_from_log._speed` 가 고쳤다.)
r = R.score(m(arrive={"stopped_ever": False, "reached": False, "nearest_edge_mm": 79.0}))
check("안 멈춤", got(r, "arrived"), False)
check("안 멈추면 held 도 False (None 아님)", got(r, "held"), False)
check("안 멈춰도 no_hit 은 채점한다", got(r, "no_hit"), True)

r = R.score(m(arrive={"stopped_ever": True, "reached": False, "nearest_edge_mm": 175.0}))
check("멈췄지만 구역 밖", got(r, "arrived"), False)
check("구역 밖이면 held 도 False", got(r, "held"), False)

# ── Sub 2# 들고 있었는가는 **로봇 전체**다 (시트가 그리퍼와 갈라 놓았다) ─────────────────
# 바퀴 베이스에 얹어 나른 판.  앞 판(30점)에서는 0점이었고 지금은 통과다.
check("베이스에 얹어 나름", got(R.score(m(arrive={"held": True})), "held"), True)
check("로봇 아닌 것이 받침", got(R.score(m(arrive={"held": False})), "held"), False)

# ── ALL 1# 충돌은 판을 끝낸다 ─────────────────────────────────────────────────────────
r = R.score(m(ended="hit",
              furniture={"hit": True, "worst_mm": 163.3, "what": "Kit_11_gondola",
                         "part": "crate", "frames": 2550}))
check("충돌 no_hit", got(r, "no_hit"), False)
check("충돌이면 placed 0점", got(r, "placed"), False)
check("충돌이면 stayed 0점", got(r, "stayed"), False)
check("충돌 판도 집기는 채점", got(r, "picked"), True)
check("충돌 판 총점", r["total"], 3.0 + 3.0 + 4.0)

# ── 낙하도 판을 끝낸다 ───────────────────────────────────────────────────────────────
r = R.score(m(ended="dropped"))
check("낙하면 placed 0점", got(r, "placed"), False)
check("낙하면 stayed 0점", got(r, "stayed"), False)
check("낙하 판도 no_hit 은 채점", got(r, "no_hit"), True)

# ── Sub 3# 얹기 -- 걸침은 **여기서 안 본다**, 대신 책상 20 mm ──────────────────────────
# 시트: "여기는 얹히기(책상 상판과 접촉)만 하면 됨."
check("걸침이 커도 얹기는 통과",
      got(R.score(m(place={"overhang_mm": 200.3})), "placed"), True)
check("상판에서 뜸", got(R.score(m(place={"seat_mm": 40.0})), "placed"), False)
check("책상 근처도 안 감",
      got(R.score(m(place={"reached_desk": False})), "placed"), False)
# 책상 밀림 문턱이 5 -> 20 mm 로 바뀌었다.  앞 판이라면 아래 첫 줄이 0점이었다.
check("책상 15 mm 밀림은 통과", got(R.score(m(desk={"worst_mm": 15.0})), "placed"), True)
check("책상 25 mm 밀림은 0점", got(R.score(m(desk={"worst_mm": 25.0})), "placed"), False)

# ── Sub 3# 6초 창 -- 걸침은 빠지고 세 조건이다 ────────────────────────────────────────
# 사용자 결정 2026-09-02: "나란히 놓지 않아도 돼.  그냥 놓고 6초동안 떨어지지 않으면 돼."
# 실측된 우리 놓기가 72.1 / 84.0 / 96.0 / 113.7 / 200.3 mm 로 전부 옛 문턱 30 을 넘었는데,
# **이제 전부 통과해야 한다.**  이 세 줄이 그 결정을 지킨다.
check("걸침 200.3 도 통과", got(R.score(m(watch={"overhang_mm": 200.3})), "stayed"), True)
check("걸침 72.1 도 통과", got(R.score(m(watch={"overhang_mm": 72.1})), "stayed"), True)
check("걸침 12.0 도 통과", got(R.score(m(watch={"overhang_mm": 12.0})), "stayed"), True)
check("걸침은 채점에 안 쓴다", R.OVERHANG_SCORED, False)
# **떨어지는 것은 여전히 잡아야 한다.**  걸침을 뺀 것이 "아무거나 통과" 가 되면 안 된다.
check("상판에서 굴러떨어짐", got(R.score(m(watch={"seat_mm": -700.0})), "stayed"), False)
# 걸침 숫자는 통과 문장에도 남아 있어야 한다 -- 나중에 다시 채점에 쓸 수 있어야 하므로
check("걸침 숫자를 통과 문장에도 남긴다",
      "200.3" in R.score(m(watch={"overhang_mm": 200.3}))["items"]["stayed"]["why"], True)
# 넘어진 편은 106.7~113.1 도였고 정상 편은 0.15~1.23 도다.  사이가 통째로 비어 있다.
check("넘어짐", got(R.score(m(watch={"tilt_deg": 106.7})), "stayed"), False)
check("받침 뜸", got(R.score(m(watch={"seat_mm": 9.0})), "stayed"), False)
check("창 끝에 아직 움직임", got(R.score(m(watch={"tail_speed_mm_s": 25.0})), "stayed"), False)
check("손을 안 뗌", got(R.score(m(watch={"opened": False})), "stayed"), False)
r = R.score(m(watch={"opened": None}))
check("손 뗐는지 못 읽음 = None", got(r, "stayed"), None)
check("못 읽으면 분모에서 빠짐", r["possible"], 17.0)

# ── 발자국 겹침 규칙 (`zone_gap_mm`) ─────────────────────────────────────────────────
GOAL = (-0.1003, 2.5588)
near("목표 위", R.zone_gap_mm(GOAL, 0.0, GOAL), 0.0)
# 앞끝이 0.225 m 이므로 0.30 m 뒤에 서면 0.075 가 남고 반경 0.10 이 그것을 덮는다
near("뒤로 0.30 m", R.zone_gap_mm((GOAL[0] - 0.30, GOAL[1]), 0.0, GOAL), 0.0)
# 0.50 m 뒤: 0.50 - 0.225 = 0.275, 반경 빼면 0.175
near("뒤로 0.50 m", R.zone_gap_mm((GOAL[0] - 0.50, GOAL[1]), 0.0, GOAL), 175.0)
# 옆으로 0.50 m: 0.50 - 0.301 = 0.199, 반경 빼면 0.099
near("옆으로 0.50 m", R.zone_gap_mm((GOAL[0], GOAL[1] + 0.50), 0.0, GOAL), 99.0)
# **우리 GT 가 여기 걸린다.**  중심으로는 179 mm 라 옛 기준(중심 100 mm)에서 0점이었고,
# 발자국 기준에서는 통과다.  이 한 줄이 사용자 결정 2026-09-02 의 결과다.
near("우리 GT 의 179 mm", R.zone_gap_mm((GOAL[0] - 0.179, GOAL[1]), 0.0, GOAL), 0.0)
# 방위를 돌리면 답이 달라져야 한다 -- 사각형이지 원이 아니다.
#
# **옆으로 선 쪽이 오히려 가깝다.**  베이스는 앞으로 0.225 m 밖에 안 뻗는데 옆으로는
# 0.301 m 뻗기 때문이다 (`ROBOT_FOOTPRINT`, FFW_SG2.usd 의 base_mobile_assy).
# 처음에 반대로 적었다가 이 시험에 걸렸다 -- 치수를 안 보고 "앞이 길겠지" 라고 짐작한 것이다.
#
#   앞으로 향함   0.45 - 0.225(앞끝) - 0.10(반경) = 0.125 m
#   90도 돌아섬   0.45 - 0.301(반폭) - 0.10(반경) = 0.049 m
near("0.45 m 뒤, 앞을 향함", R.zone_gap_mm((GOAL[0] - 0.45, GOAL[1]), 0.0, GOAL), 125.0)
near("0.45 m 뒤, 옆으로 섬", R.zone_gap_mm((GOAL[0] - 0.45, GOAL[1]), 1.5707963, GOAL), 49.0)
# 뒤로는 0.403 m 뻗으므로 등을 돌리면 가장 가깝다
near("0.45 m 뒤, 등을 돌림",
     R.zone_gap_mm((GOAL[0] - 0.45, GOAL[1]), 3.14159265, GOAL), 0.0)

# ── 시도 3회 합산 ────────────────────────────────────────────────────────────────────
a = R.score(m())                                   # 21
b = R.score(m(ended="dropped"))                    # 놓기 7점 날아감 -> 14
c = R.score(m(ended="hit", furniture={"hit": True, "worst_mm": 5.0}))   # 10
t3 = R.total([a, b, c])
check("3판 합", t3["total"], a["total"] + b["total"] + c["total"])
check("3판 만점", t3["full"], 63.0)
check("3판 개수", t3["attempts"], 3)
# 두 판만 돌렸으면 **모자란 판을 0점으로 세지 않는다** -- 안 돌린 판과 0점 판은 다르다
t2 = R.total([a, b])
check("2판만 돌림", t2["attempts"], 2)
check("2판 분모", t2["possible"], a["possible"] + b["possible"])

# ── 문턱이 시트대로인가 ──────────────────────────────────────────────────────────────
check("들림 30 mm", R.LIFT_OK_MM, 30.0)
check("구역 반경 0.10 m", R.ARRIVE_ZONE_M, 0.10)
check("멈춤 10 mm/s", R.STOP_MM_S, 10.0)
check("받침 5 mm", R.SEAT_ON_MAX_MM, 5.0)
check("걸침 30 mm (값은 남기되 채점엔 안 씀)", R.OVERHANG_OK_MM, 30.0)
check("기울기 15도", R.TILT_OK_DEG, 15.0)
check("감시창 6초", R.WATCH_S, 6.0)
check("창 꼬리 0.5초", R.WATCH_TAIL_S, 0.5)
check("책상 20 mm", R.DESK_OK_MM, 20.0)
check("제한 20분", R.TIME_LIMIT_S, 1200.0)


# ══════════════════════════════════════════════════════════════════════════════════════
# 2026-09-07 사용자 결정 세 가지.  **이 절이 깨지면 결정이 되돌려진 것이다.**
# ══════════════════════════════════════════════════════════════════════════════════════

import numpy as np  # noqa: E402
import score_from_log as SFL  # noqa: E402

# ── ② 마지막 놓기 ─────────────────────────────────────────────────────────────────────
# "놓았다가 다시 들었다가 또 놓는 경우에는 마지막 놓기를 기준으로."
#
# `rel[i]` 은 i 번째 프레임에 바구니가 로봇에게서 떨어져 상판 위에 있었나다.
# 기록은 초당 10 장이므로 `t` 는 0.1 초 간격이다.
_t = np.arange(40) * 0.1


def _rel(*spans):
    """`spans` 로 준 구간만 True 인 배열.  구간은 (시작, 끝) 프레임 번호."""
    r = np.zeros(40, bool)
    for a, b in spans:
        r[a:b] = True
    return r


# 한 번만 놓았다 -> 그 자리가 시작이다
check("놓기 한 번: 횟수", SFL._last_release(_rel((10, 40)), _t)[0], 1)
check("놓기 한 번: 시작", SFL._last_release(_rel((10, 40)), _t)[1], 10)

# 놓고(10) -> 1.0 초 다시 잡고(15~25) -> 다시 놓음(25).  **뒤엣것을 쓴다**
check("재파지 1.0초: 횟수", SFL._last_release(_rel((10, 15), (25, 40)), _t)[0], 2)
check("재파지 1.0초: 시작", SFL._last_release(_rel((10, 15), (25, 40)), _t)[1], 25)

# 판정이 한 프레임(0.1 초) 튄 것은 재파지가 아니다 -> 첫 놓기가 그대로 시작이다
check("깜빡임 0.1초: 횟수", SFL._last_release(_rel((10, 20), (21, 40)), _t)[0], 1)
check("깜빡임 0.1초: 시작", SFL._last_release(_rel((10, 20), (21, 40)), _t)[1], 10)

# 문턱(0.5 초) 바로 위/아래.  4 프레임은 0.4 초라 깜빡임, 5 프레임은 0.5 초라 재파지다.
check("0.4초 비었음 -> 깜빡임", SFL._last_release(_rel((10, 20), (24, 40)), _t)[0], 1)
check("0.5초 비었음 -> 재파지", SFL._last_release(_rel((10, 20), (25, 40)), _t)[0], 2)

# 손을 끝내 안 뗐다
check("손 안 뗌: 횟수", SFL._last_release(np.zeros(40, bool), _t)[0], 0)
check("손 안 뗌: 시작", SFL._last_release(np.zeros(40, bool), _t)[1], None)

# 세 번 놓았으면 세 번째다
check("놓기 세 번", SFL._last_release(_rel((5, 10), (18, 23), (30, 40)), _t)[1], 30)

# ── ② 딸림: 감시창이 6 초를 못 채우면 0 점 ────────────────────────────────────────────
# 마지막 놓기로 옮기면 창이 뒤로 밀려 짧아질 수 있다.  짧으면 **못 잰 것이 아니라 못 보인
# 것**이므로 미채점(None)이 아니라 0 점이다.
check("창 6.0초 -> 통과", got(R.score(m(watch={"window_s": 6.0})), "stayed"), True)
check("창 2.0초 -> 0점", got(R.score(m(watch={"window_s": 2.0})), "stayed"), False)
check("창 5.9초 -> 0점", got(R.score(m(watch={"window_s": 5.9})), "stayed"), False)
check("창 길이 미상 -> 예전대로",
      got(R.score(m(watch={"window_s": None})), "stayed"), True)
# 창이 짧다고 분모에서 빠지면 안 된다 -- 적게 할수록 유리해지는 구멍을 늘리는 짓이다
check("창 짧음은 분모에 남는다",
      R.score(m(watch={"window_s": 2.0}))["possible"], 21.0)

# ── ① 손을 끝내 안 뗐으면 0 점 (회귀 방지) ────────────────────────────────────────────
check("손 안 뗌 -> 0점", got(R.score(m(watch={"opened": False})), "stayed"), False)
check("손 뗐는지 모름 -> 미채점", got(R.score(m(watch={"opened": None})), "stayed"), None)

# ── ③ 뒤집혀 얹힌 것은 얹은 것이 아니다 ───────────────────────────────────────────────
# 높이만 보면 거꾸로 엎어 놓아도 통과한다.  **같은 프레임에서** 얹힘과 똑바름을 둘 다
# 만족해야 한다 -- 따로 보면 뒤집힌 채 얹혔다가 나중에 공중에서 똑바로 선 판도 통과한다.
check("똑바로 얹힘 -> 통과", got(R.score(m()), "placed"), True)
check("뒤집혀 얹힘 -> 0점",
      got(R.score(m(place={"tilt_deg": 170.0, "seated_any": True, "upright_any": False})),
          "placed"), False)
# 얹힌 순간은 기울었고 똑바른 순간은 떠 있었다 -> 같은 프레임 규칙에 걸린다
check("얹힘과 똑바름이 따로 -> 0점",
      got(R.score(m(place={"tilt_deg": 90.0, "seated_any": True, "upright_any": False})),
          "placed"), False)
# 뒤집힘은 **못 잰 것이 아니다** -- 분모에 남아야 한다
check("뒤집힘은 분모에 남는다",
      R.score(m(place={"tilt_deg": 170.0, "seated_any": True, "upright_any": False}))["possible"],
      21.0)
# 옛 로그(열쇠가 아예 없는 것)는 예전처럼 높이만 본다
check("upright_any 없으면 예전대로",
      got(R.score(m(place={"reached_desk": True, "seat_mm": 1.5, "overhang_mm": 12.0})),
          "placed"), True)

# ── ④ 걸침은 채점하지 않는다 (회귀 방지) ──────────────────────────────────────────────
# "책상 끝에 반쯤 걸쳐 놓더라도, 6초 두고 책상 위에 있다고만 하면 점수 인정이야."
check("걸침 200 mm 여도 얹힘 통과",
      got(R.score(m(place={"overhang_mm": 200.0})), "placed"), True)
check("걸침 200 mm 여도 6초 통과",
      got(R.score(m(watch={"overhang_mm": 200.0})), "stayed"), True)
check("걸침은 채점 대상이 아니다", R.OVERHANG_SCORED, False)

# ── 세 변경이 서로를 깨지 않는가 ──────────────────────────────────────────────────────
check("셋 다 정상이면 만점", R.score(m())["total"], 21.0)


if FAIL:
    print(f"실패 {len(FAIL)}건")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print(f"전부 통과 ({len(R.ITEMS)}항목 {sum(R.POINTS.values()):.0f}점 × 시도 {R.ATTEMPTS} = "
      f"{sum(R.POINTS.values()) * R.ATTEMPTS:.0f}점)")
print()
print(R.render(R.score(m())))
print()
print(R.render_total(R.total([R.score(m()), R.score(m(ended="dropped")),
                              R.score(m(ended="hit", furniture={"hit": True, "worst_mm": 5.0}))])))
