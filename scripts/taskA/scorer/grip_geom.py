# Copyright 2025.
#
# **손이 바구니를 쥐고 있었는가를 힘이 아니라 자리로 판정한다.**  numpy 말고는 아무것도
# import 하지 않는다 -- 시뮬레이터 없이 돌아야 한다.
#
# WHY THIS EXISTS
#   평가표는 "그 시점에 로봇이 바구니를 들고 있었는가" 를 묻는다.  접촉력은 **물리를 돌려야만
#   나오는 값**이고 기록에는 없다.  그래서 `gt_replay.py` 가 기록을 물리와 함께 다시 돌렸는데,
#   **긴 주행에서 재현되지 않았다** (2026-09-02 실측):
#
#       seed 0  11.5 m   3102/3102 프레임 유지        ✓
#       seed 1  18.1 m   41.5초에 놓침 -- 스워브가 잠겼다 풀리며 베이스가 1.39 m/s 로 튄다
#       seed 2  24.7 m   더 일찍 놓침
#
#   튀기 직전까지 그리퍼 힘은 중앙 40 N 으로 멀쩡했다 (415 프레임 동안 1 N 아래로 내려간 적이
#   없다).  쥐는 힘의 문제가 아니라 **다시 모는 과정**의 문제이므로, `--grip_follow` 를 네 값
#   (0.008/0.015/0.030/0.060), 속도 상한을 두 값(0.45/0.25), 베이스 방식을 두 가지(추종/기록
#   명령)로 돌려도 풀리지 않았다.
#
#   그러므로 **물리를 안 돌리고 판정한다.**  기록에는 손가락 링크 8 개의 자리와 바구니 자세가
#   프레임마다 들어 있고, 그것으로 충분하다는 것을 아래처럼 확인했다.
#
# ---------------------------------------------------------------- 무엇으로 판정하나
#
#   한 손이 바구니를 쥐고 있다  <=>  ① 그 손의 링크 하나라도 바구니 표면에서 NEAR_MM 안이고
#                                    ② 그 손의 두 끝마디 사이 벌림이 GAP_MM 이하다
#   로봇이 쥐고 있다            <=>  두 손 중 하나라도 그렇다
#
#   ①만으로는 **놓은 뒤에도 손이 옆에 남아 있는 구간**이 통과한다 (놓기 2,409 프레임 중
#   1,790 이 그렇게 잡혔다).  ②가 그것을 가른다 -- 쥐면 좁고 놓으면 활짝 벌어진다.
#
# ---------------------------------------------------------------- 물리와 얼마나 맞나
#
#   seed 0·1·2 의 **바구니를 끝까지 들고 있던 조각 7 개**에서, 물리로 잰 접촉(그리퍼 8 개 중
#   최대 힘 > 0.5 N)을 정답으로 놓고 프레임마다 대조했다 (2026-09-02).
#
#       집기 1,530 프레임    99.5 %    오탐 3   미탐 4
#       주행 3,102 프레임   100.0 %    오탐 0   미탐 0
#       놓기 2,409 프레임    99.9 %    오탐 2   미탐 0
#       ----------------------------------------------
#       전체 7,041 프레임    99.9 %    오탐 5   미탐 4
#
#   **먼저 시험했다가 버린 판정도 적어 둔다.**  `scoring/grasp_geom.opposite_walls` 의
#   "양손이 서로 다른 벽을 낀다" 는 편마다 답이 뒤집혔다 -- 같은 집기인데 seed 2 는 96.5 %
#   (미탐 0), seed 0·1 은 13.9 % (미탐 423).  손가락이 벽을 정면으로 끼면 잡히고 살짝 비껴
#   걸치면 안 잡힌다.  **편마다 다른 잣대는 채점에 못 쓴다.**
#
# ---------------------------------------------------------------- 두 문턱의 출처
#
#   이 저장소는 "우리 실행 분포에서 고른 값" 을 문턱으로 쓰는 것을 금지한다 -- 참가자에게
#   우리 궤적을 따라오라고 요구하는 셈이 되기 때문이다.  **이 둘은 성격이 다르다:
#   합격선이 아니라 "접촉을 어떻게 읽을 것인가" 라는 계측 방법**이고, 물리로 잰 것과
#   99.9 % 일치한다는 근거가 있다.  그래도 어디서 나왔는지 그대로 적는다.
#
#   NEAR_MM 40   손가락 링크의 **원점**은 표면이 아니라 링크 중심이라 늘 얼마쯤 떨어져 있다.
#                물리가 "닿았다" 고 한 링크의 거리가 5~95 % 구간에서 5.7 ~ 38.1 mm.
#   GAP_MM 60    쥐었을 때 벌림 22.9 ~ 50.9 mm,  놓았을 때 45.5 ~ 114.7 mm (중앙 114.7).
#                60 을 두면 놓기 2,409 프레임이 100.0 % 맞는다.

import numpy as np

# 링크 순서는 `scene_spec.GRIP_LINKS` 그대로다:
#   0 l_l1  1 l_l2  2 l_r1  3 l_r2   |   4 r_l1  5 r_l2  6 r_r1  7 r_r2
# 각 손의 **끝마디**는 l2 와 r2 -- 벌림은 그 둘 사이 거리다.
LEFT = (0, 1, 2, 3)
RIGHT = (4, 5, 6, 7)
LEFT_TIPS = (1, 3)
RIGHT_TIPS = (5, 7)

NEAR_MM = 40.0
GAP_MM = 60.0

# 바구니 치수.  `scoring/grasp_geom.py` 와 같은 값을 다시 적지 않고 거기서 읽는다 --
# 두 곳에 적으면 상자가 바뀌는 날 조용히 갈라진다.


def _crate_half(along, across, height):
    return np.array([along / 2.0, across / 2.0, height / 2.0], dtype=np.float64)


def _qconj(q):
    out = np.array(q, dtype=np.float64, copy=True)
    out[..., 1:] *= -1.0
    return out


def _qapply(q, v):
    """wxyz 쿼터니언으로 벡터를 돌린다.  (T,4) x (T,3) 를 한꺼번에."""
    q = np.asarray(q, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    w, u = q[..., :1], q[..., 1:]
    t = 2.0 * np.cross(u, v)
    return v + w * t + np.cross(u, t)


def surface_dist_m(pts, crate_pos, crate_quat, size):
    """손가락 자리에서 바구니 **표면**까지의 거리 (m).  음수면 상자 안쪽.

    `pts` 는 (T, K, 3), 돌려주는 것은 (T, K).  바구니 원점이 밑면이므로 중심으로 옮겨서 잰다
    (`task_layout.BASKET_ORIGIN_LIFT = 0`).
    """
    pts = np.asarray(pts, dtype=np.float64)
    cp = np.asarray(crate_pos, dtype=np.float64)
    cq = np.asarray(crate_quat, dtype=np.float64)
    half = _crate_half(*size)
    T, K = pts.shape[0], pts.shape[1]
    rel = pts - cp[:, None, :]
    qc = _qconj(cq)[:, None, :].repeat(K, axis=1)
    loc = _qapply(qc, rel)
    loc[..., 2] -= half[2]
    d = np.abs(loc) - half[None, None, :]
    outside = np.linalg.norm(np.maximum(d, 0.0), axis=-1)
    inside = np.minimum(d.max(axis=-1), 0.0)
    return outside + inside


def jaw_gap_mm(grip_pos):
    """두 손의 벌림 (mm).  (T, 8, 3) -> (T, 2), 왼손 먼저."""
    g = np.asarray(grip_pos, dtype=np.float64)
    l = np.linalg.norm(g[:, LEFT_TIPS[0]] - g[:, LEFT_TIPS[1]], axis=-1)
    r = np.linalg.norm(g[:, RIGHT_TIPS[0]] - g[:, RIGHT_TIPS[1]], axis=-1)
    return np.stack([l, r], axis=1) * 1000.0


def held(grip_pos, crate_pos, crate_quat, size, near_mm=NEAR_MM, gap_mm=GAP_MM):
    """프레임마다 "로봇이 바구니를 쥐고 있었나".

    돌려주는 것: (held(T,), 손별 판정(T,2), 손별 최단거리 mm (T,2), 손별 벌림 mm (T,2))
    **손별로 따로 돌려주는 이유**: 어느 손이 놓쳤는지가 로그에 남아야 이의 제기에 답할 수 있다.
    """
    d = surface_dist_m(grip_pos, crate_pos, crate_quat, size) * 1000.0
    gap = jaw_gap_mm(grip_pos)
    near = np.stack([d[:, LEFT].min(axis=1), d[:, RIGHT].min(axis=1)], axis=1)
    per_hand = (near <= near_mm) & (gap <= gap_mm)
    return per_hand.any(axis=1), per_hand, near, gap


def gripped(grip_pos, crate_pos, crate_quat, size, **kw):
    """집기(Sub 1#)가 묻는 것 -- **그리퍼**가 물었는가.

    지금은 `held` 와 같은 계산이다.  이름을 나눠 두는 이유는 평가표가 두 물음을 다른 범위로
    묻기 때문이다 (집기는 그리퍼, 이동은 로봇 전체).  로봇의 다른 부위로 받치는 판을 기하로
    가릴 방법이 생기면 여기만 갈라지면 된다.
    """
    return held(grip_pos, crate_pos, crate_quat, size, **kw)
