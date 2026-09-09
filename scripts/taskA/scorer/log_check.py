# Copyright 2025.
#
# **채점하기 전에, 이 로그가 채점할 만한 물건인지 본다.**
#
# 왜 필요한가 -- 실측 2026-09-08
#   만점 로그 하나를 가져다 비틀어 넣어 봤다.  채점기는 대부분을 그냥 통과시켰고, 하나는
#   죽었다:
#
#     base_pos 를 전부 NaN 으로        14 / 21 점.  로봇이 어디 있었는지 모르는데
#                                      「매장 가구와 부딪히지 않았다」 4 점을 준다
#     베이스를 순간이동시킴             21 / 21 점.  주행 없이 목적지에 나타난다
#     시계를 전부 0 으로               17 / 21 점.  제한 시간이 의미를 잃는다
#     hit_now 를 전부 NaN 으로         ValueError 로 **죽는다**
#
#   NaN 이 특히 나쁘다.  NaN 은 무엇과 비교해도 거짓이라, "부딪혔나?" 가 **조용히**
#   "아니오" 가 된다.  못 재서 0 점이 되는 것이 아니라 **못 쟀는데 만점**이 된다.
#
# 무엇을 하나
#   `problems()` 가 이상한 점의 목록을 돌려준다.  비어 있으면 채점해도 된다.  하나라도
#   있으면 `taska_score.py` 는 **점수를 내지 않고** 그 목록을 찍는다.
#
#   점수를 0 으로 매기지 않는 이유: 로그가 깨진 것은 로봇이 못한 것과 다르다.  하네스나
#   시뮬레이터가 튀어서 깨졌을 수도 있고, 그때 0 점을 주면 참가자가 억울하다.  채점기는
#   「이 로그로는 채점할 수 없다 + 왜」까지만 말하고 판단은 사람이 한다.
#
# 문턱은 어디서 왔나 -- **정답 주행 세 판을 재서 얻었다** (2026-09-08)
#
#     프레임 간격        정확히 0.100 초 (세 판 모두, 편차 없음)
#     베이스 최대 속도    0.68 m/s
#     바구니 최대 속도    0.66 m/s
#     쿼터니언 크기       정확히 1.0000
#
#   순간이동 문턱을 3.0 m/s 로 잡은 것은 실측 최대의 4.4 배다.  참가자 로봇이 우리보다
#   훨씬 빨라도 걸리지 않고, 한 프레임에 몇 미터를 뛰는 것은 걸린다.  FFW-SG2 의 스워브
#   베이스는 3 m/s 로 달리지 않는다.
#
# 순수 numpy 다.  Isaac 도, 씬 파일도, 이미지도 필요 없다.

import numpy as np

import rubric_taskA as R

# 채점기가 읽는 갈래 전부.  `Task-A/eval_kit/make_demos.py` 의 `SCORE_FIELDS` 와 같은
# 목록이고, 하나라도 없으면 채점이 성립하지 않는다.
REQUIRED = ("t", "base_pos", "base_quat", "base_vel",
            "crate_pos", "crate_quat", "crate_vel",
            "crate_robot_force", "crate_other_force", "crate_nonrobot_force",
            "desk_pos", "desk_quat", "grip_pos", "grip_force",
            "hit_now", "hit_depth_mm")

QUATS = ("base_quat", "crate_quat", "desk_quat")
POSES = ("base_pos", "crate_pos", "desk_pos")

# 한 프레임에 이만큼보다 빨리 움직이면 순간이동으로 본다 (m/s).  근거는 머리말.
MAX_SPEED_M_S = 3.0

# 쿼터니언 크기가 1 에서 이만큼보다 벗어나면 정규화가 안 된 것이다.
QUAT_TOL = 1e-3

# 프레임 간격이 중앙값의 이 배수를 벗어나면 일정하지 않다고 본다.  넉넉히 잡았다 --
# 참가자 하네스가 우리와 다른 주기로 기록할 수 있고, 그것 자체는 잘못이 아니다.
# 잡으려는 것은 "중간에 시계가 튀거나 멈추는" 것이다.
DT_LOW, DT_HIGH = 0.2, 5.0

# 매장의 범위 (m).  `scripts/taskA/taskA_layout.py` 의 STORE_X / STORE_Y 와 같은 값이고,
# 여기 다시 적는 이유는 이 파일이 배포 이미지 없이도 돌아야 하기 때문이다 (그쪽은
# 매장 USD 경로를 잡느라 이미지를 본다).  값이 갈라지면 아래 시험이 잡는다.
# **채점 규칙 쪽에서 가져온다.**  매장 이탈이 판 종료 조건이 되면서(2026-09-10) 이 값은
# 위생 검사만의 것이 아니게 됐다.  두 곳에 적으면 언젠가 갈라진다.
STORE_X = R.STORE_X
STORE_Y = R.STORE_Y
BOUND_MARGIN_M = 2.0        # 벽 밖 2 m 까지는 봐준다.  잡으려는 것은 좌표가 통째로 깨진 것


def _finite_name(a, key):
    v = np.asarray(a[key], dtype=np.float64)
    bad = ~np.isfinite(v)
    return int(bad.sum())


def scene_problems(a, scene):
    """**씬이 말이 되는 물건인가.**  이상한 점의 목록.  비어 있으면 된다.

    이 검사가 왜 있나 -- 채점기는 로그(로봇이 어디 있었나)는 전수로 검사하면서 **씬(책상이
    어디 있나)은 그냥 믿고 있었다.**  그런데 도착 항목 7 점이 통째로 씬의 책상 좌표 위에
    서 있다.  구역의 중심이 책상이고 반지름이 |목표 − 책상| 이기 때문이다.

    씬이 틀리는 길은 공격이 아니라 **우리 실수**다.  두 좌표는
    `scripts/taskA/destinations.json` 에서 오고, 그것은 매장 USD 를 다시 구울 때마다 다시
    뽑아야 하는 파생 파일이다.  40 cm 어긋나게 뽑히면 구역이 40 cm 옮겨가는데 **오류도
    경고도 안 나고 점수는 그럴듯하게 나온다.**  채점이 다 끝난 뒤에야 드러난다.

    대조할 수 있는 이유는 책상과 목적지가 **매장 붙박이**라서다 -- seed 가 무엇이든 같은
    자리이고, 세 장면에서 소수 넷째 자리까지 같은 것을 확인했다.

    로그의 책상과도 맞춰 본다.  둘이 어긋나면 씬과 로그가 서로 다른 판의 것이다.
    """
    import math
    out = []
    if not isinstance(scene, dict):
        return ["씬이 없다 -- 도착 판정은 책상 좌표 없이 성립하지 않는다"]

    want = {"desk": R.FIXTURE_DESK_XY, "goal": R.FIXTURE_GOAL_XY}
    got = {}
    for key in ("desk", "goal"):
        blk = scene.get(key)
        if not isinstance(blk, dict):
            out.append("씬에 '%s' 가 없다 -- 도착 구역을 정할 수 없다" % key)
            continue
        # 책상은 pos(3), 목적지는 xy(2) 로 실려 온다.  둘 다 없으면 그것도 이상이다.
        xy = blk.get("pos") or blk.get("xy")
        if xy is None or len(xy) < 2:
            out.append("씬의 %s 에 좌표가 없다" % key)
            continue
        try:
            x, y = float(xy[0]), float(xy[1])
        except (TypeError, ValueError):
            out.append("씬의 %s 좌표를 숫자로 읽을 수 없다: %r" % (key, xy[:2]))
            continue
        if not (math.isfinite(x) and math.isfinite(y)):
            out.append("씬의 %s 좌표가 숫자가 아니다 (NaN·무한대)" % key)
            continue
        got[key] = (x, y)
        d = math.dist((x, y), want[key])
        if d > R.DESK_OK_MM / 1000.0:
            out.append("씬의 %s 가 매장 붙박이 자리에서 %.3f m 어긋나 있다 "
                       "-- 있어야 할 곳 (%.4f, %.4f), 씬이 말하는 곳 (%.4f, %.4f) "
                       "(허용 %.0f mm).  destinations.json 을 다시 뽑았나?"
                       % (key, d, want[key][0], want[key][1], x, y, R.DESK_OK_MM))

    # 씬의 책상 vs 로그 첫 프레임의 책상.  같은 판의 것이어야 한다.
    if "desk" in got and isinstance(a, dict) and "desk_pos" in a:
        dp = np.asarray(a["desk_pos"], dtype=np.float64)
        if dp.ndim == 2 and dp.shape[0] > 0 and np.isfinite(dp[0, :2]).all():
            d = float(np.hypot(*(dp[0, :2] - np.asarray(got["desk"]))))
            if d > R.DESK_OK_MM / 1000.0:
                out.append("씬이 말하는 책상과 로그 첫 프레임의 책상이 %.3f m 어긋난다 "
                           "-- 씬과 로그가 서로 다른 판의 것인가 (허용 %.0f mm)"
                           % (d, R.DESK_OK_MM))
    return out


def problems(a, head=None, scene=None):
    """이 로그를 채점해도 되는가.  이상한 점의 목록을 돌려준다 -- 비어 있으면 된다.

    `scene` 을 주면 씬도 같이 본다 (`scene_problems`).  `head` 는 아직 안 쓰지만 자리를
    남겨 둔다 -- 나중에 머리말과 배열을 대조하게 되면 여기가 그 자리다.
    """
    out = []
    if scene is not None:
        out += scene_problems(a, scene)

    # ── 있어야 할 것이 다 있나 ──────────────────────────────────────────────────────
    missing = [k for k in REQUIRED if k not in a]
    if missing:
        out.append("채점에 필요한 값이 없다: %s" % ", ".join(missing))
        return out                      # 없는 것을 재려 들면 그 다음이 전부 헛돈다

    n = len(np.asarray(a["t"]))
    if n < 2:
        out.append("프레임이 %d 개뿐이다 (둘 이상이어야 한다)" % n)
        return out
    for k in REQUIRED:
        m = len(np.asarray(a[k]))
        if m != n:
            out.append("%s 의 길이가 %d 인데 시계는 %d 다" % (k, m, n))
    if out:
        return out

    # ── 숫자가 숫자인가 ─────────────────────────────────────────────────────────────
    # NaN 은 무엇과 비교해도 거짓이라 **조용히** 통과한다.  가장 먼저 잡는다.
    for k in REQUIRED:
        bad = _finite_name(a, k)
        if bad:
            out.append("%s 에 숫자가 아닌 값(NaN·무한대)이 %d 개 있다" % (k, bad))

    # ── 시계 ────────────────────────────────────────────────────────────────────────
    t = np.asarray(a["t"], dtype=np.float64)
    if np.isfinite(t).all():
        dt = np.diff(t)
        if (dt <= 0).any():
            k = int((dt <= 0).sum())
            out.append("시계가 앞으로 가지 않는 자리가 %d 곳 있다 "
                       "(멈춰 있거나 거꾸로 간다)" % k)
        elif dt.size:
            med = float(np.median(dt))
            odd = int(((dt < med * DT_LOW) | (dt > med * DT_HIGH)).sum())
            if odd:
                out.append("프레임 간격이 일정하지 않다 -- 중앙값 %.3f 초인데 "
                           "%.3f~%.3f 초 밖인 자리가 %d 곳" % (med, med * DT_LOW,
                                                              med * DT_HIGH, odd))

    # ── 쿼터니언 ────────────────────────────────────────────────────────────────────
    for k in QUATS:
        q = np.asarray(a[k], dtype=np.float64)
        if not np.isfinite(q).all():
            continue
        nrm = np.linalg.norm(q, axis=1)
        off = np.abs(nrm - 1.0)
        if off.max() > QUAT_TOL:
            out.append("%s 가 정규화돼 있지 않다 (크기가 최대 %.4f 만큼 어긋난다)"
                       % (k, float(off.max())))

    # ── 순간이동 ────────────────────────────────────────────────────────────────────
    if np.isfinite(t).all() and t.size > 1 and (np.diff(t) > 0).all():
        dt = np.diff(t)
        for k in ("base_pos", "crate_pos"):
            p = np.asarray(a[k], dtype=np.float64)[:, :3]
            if not np.isfinite(p).all():
                continue
            step = np.linalg.norm(np.diff(p, axis=0), axis=1)
            v = step / dt
            if v.max() > MAX_SPEED_M_S:
                i = int(np.argmax(v))
                out.append("%s 가 한 프레임에 %.2f m 움직였다 (%.1f m/s, %d 번째 프레임) "
                           "-- 순간이동이다 (문턱 %.1f m/s, 정답 주행 최대 0.68)"
                           % (k, float(step[i]), float(v[i]), i, MAX_SPEED_M_S))

    # ── 좌표가 매장 안인가 ──────────────────────────────────────────────────────────
    for k in POSES:
        p = np.asarray(a[k], dtype=np.float64)
        if not np.isfinite(p).all():
            continue
        x, y = p[:, 0], p[:, 1]
        if (x.min() < STORE_X[0] - BOUND_MARGIN_M or x.max() > STORE_X[1] + BOUND_MARGIN_M
                or y.min() < STORE_Y[0] - BOUND_MARGIN_M or y.max() > STORE_Y[1] + BOUND_MARGIN_M):
            out.append("%s 가 매장 밖으로 나간다 (x %.1f~%.1f, y %.1f~%.1f; "
                       "매장은 x %.1f~%.1f, y %.1f~%.1f)"
                       % (k, x.min(), x.max(), y.min(), y.max(),
                          STORE_X[0], STORE_X[1], STORE_Y[0], STORE_Y[1]))

    return out


def report(probs, name=""):
    """사람이 읽는 한 덩어리.  `taska_score.py` 가 거부할 때 찍는다."""
    head = "[채점 불가] %s" % name if name else "[채점 불가]"
    lines = [head, "  이 로그는 채점할 수 없습니다. 아래를 확인해 주십시오.", ""]
    for p in probs:
        lines.append("  * %s" % p)
    lines += ["", "  점수를 0 으로 매기지 않았습니다 -- 로그가 깨진 것과 로봇이 못한 것은",
              "  다른 일이기 때문입니다."]
    return "\n".join(lines)
