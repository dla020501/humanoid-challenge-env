# Copyright 2025.
#
# seed 하나가 장면 하나를 정하는 **규칙**. 여기 있는 것이 그 전부다.
#
# 한 장면에서 seed 가 정하는 것은 넷이다.
#
#   좌석        시식 탁상 3 개 x 4 등분 = 12 곳 중 하나. 로봇과 바구니가 여기서 출발한다
#   매장씨앗    곤돌라 12 개와 냉장·냉동·주류 진열대에 **무엇이 서 있는지**
#   진열대씨앗  목표 진열대에 무엇이 서 있고 앞줄 어느 칸이 비어 있는지
#   바구니 옮김  좌석이 정한 바구니 자리에서 반경 20 mm 안으로 얼마나 옮기는지 (방향은 그대로)
#
# 평가표가 그렇게 정한다: *"진열대(목표 진열대 + 기타 진열대)에 진열되어 있는 상품은 랜덤
# (진열대 자체의 배치는 달라지지 않음)"*. **자리는 안 바뀌고 물건만 바뀐다** -- 그래서
# 충돌 판정이 보는 발자국은 seed 와 무관하고, 정책이 보는 그림만 매번 달라진다.
#
# 좌석 규칙은 `task_a_demo.py` 가 이미 쓰던 것을 그대로 옮겼다
#
#   n = (seed * 7919) % 12
#
# `7919 % 12 == 11` 이므로 이것은 사실상 `(12 - seed) % 12` 다. 숫자로 적으면:
#
#     seed  0  1  2  3  4  5  6  7  8  9 10 11
#     좌석  0 11 10  9  8  7  6  5  4  3  2  1
#
# **이 값을 바꾸면 안 된다.** 주최 측이 만든 정답 주행과 참가자가 받는 장면이 같은 seed 에서
# 다른 좌석이 되고, 그것은 조용히 어긋난다 -- 두 장면 다 정상으로 열리고 로봇도 잘 달린다.
#
# 왜 `random` 을 안 쓰나
#   `random.Random(seed)` 는 파이썬 판이 바뀌면 다른 수열을 낼 수 있고, 다른 언어에서는
#   재현할 방법이 아예 없다. 여기서는 md5 앞 8 자리를 정수로 읽는다 -- 파이썬이 없어도,
#   손으로도, 같은 값이 나온다.
#
#       store_seed = int(md5("taskA-eval-store|<seed>")[:8], 16) % 999999 + 1
#       shelf_seed = int(md5("taskA-eval-shelf|<seed>")[:8], 16) % 999999 + 1
#       u_r        = int(md5("taskA-eval-crate_r|<seed>")[:8], 16) / 2**32      0 이상 1 미만
#       u_th       = int(md5("taskA-eval-crate_th|<seed>")[:8], 16) / 2**32
#       바구니 옮김 = 크기 0.020 * u_r, 방향 2 pi * u_th                        (m, 월드 x·y)
#
# 이 파일은 대회 환경 저장소 `Task-A/eval_kit/scene_seed.py` 에서 **참가자 환경이 쓰는
# 부분만** 옮긴 것이다. 옮기지 않은 것을 여기 적어 둔다 -- 정답 주행을 만들 때 어느 파지를
# 시도했는지(`grasps`, `grasp_order`, `anchor`)는 수집 쪽 사정이고 장면의 일부가 아니다.
# 그것들은 `grasp_whitelist.json` 과 좌석별 `grasp_frame*.json` 을 읽어야 해서, 여기 옮기면
# 이 저장소에 쓰이지 않는 파일 열세 개가 따라 들어온다.
#
# isaaclab 도 numpy 도 안 쓴다. `task_a_demo.py --check` 가 Isaac Sim 없이 1 초에 도는 것은
# 이 파일과 `taskA_seats.py` 가 순수 파이썬이기 때문이다.
#
# 혼자 돌려 볼 수 있다:
#     python3 scripts/taskA/taskA_scene_seed.py --seed 0 1 2 1000

import hashlib
import json
import math

# `task_a_demo.py:179` 의 사상. 숫자를 바꾸면 정답 주행과 어긋난다.
SEAT_STRIDE = 7919
N_SEATS = 12

# 바구니를 좌석이 정한 자리에서 옮기는 반경의 상한.
#
# 20 mm 인 이유는 **탁상 끝까지의 여유**다. 바구니(0.380 x 0.590)는 탁상 중심에서 좌석 쪽으로
# 0.20 m 치우쳐 놓여 있어서, 기본 자리에서도 가장 먼 모서리가 탁상 끝(반지름 0.5242)까지
# 35.2 mm 밖에 안 남는다. 20 mm 를 어느 방향으로 밀어도 최악 15.2 mm 가 남는다 (12 좌석 x
# 0.1 도 간격 3600 방향, 2026-09-11). `task_a_demo.py --check` 가 이 여유를 매번 다시 잰다.
#
# **방향은 안 돌린다** (사용자 결정 2026-09-11). 돌리면 모서리가 더 멀리 나가서, 20 mm 에서는
# 7.6 도만 돌려도 여유가 거의 없어진다.
#
# **옮기는 크기를 0 ~ 20 mm 에서 고르게 뽑는다** (사용자 결정 2026-09-11: "쏠림폭이 크면 안
# 돼. 균등한 분포로"). 주최 측 수집기(`Task-A/automation/collector/run_scene_jitter.py`,
# `CRATE_SHIFT_M`)는 원 **넓이**에 고르게(크기 = 상한 x sqrt(u)) 뽑았는데, 원은 바깥 고리가
# 넓어서 그러면 큰 쪽으로 쏠린다. seed 10 만 개로 세면:
#
#                        0~5 mm   5~10 mm   10~15 mm   15~20 mm   가운데 값
#     넓이에 고르게       6 %      19 %      31 %       44 %      14.2 mm
#     크기를 고르게      25 %      25 %      25 %       25 %      10.0 mm   <- 이것
#
# 수집기는 로봇을 같이 옮겨 로봇과 바구니 사이를 그대로 두었지만, 여기서는 로봇 자리가 좌석마다
# 고정이라 바구니가 **로봇에 대해서도** 옮겨진다.
CRATE_SHIFT_M = 0.020


def _md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _draw(seed, what):
    """진열 씨앗 하나. 1 ~ 999999.

    범위는 수집기가 쓰는 것과 같다 -- 원본이 `rng.randrange(1, 10**6)` 로 뽑는다.
    """
    return int(_md5("taskA-eval-%s|%d" % (what, seed))[:8], 16) % 999999 + 1


def _unit(seed, what):
    """0 이상 1 미만의 수 하나. `_draw()` 와 같은 md5 방식."""
    return int(_md5("taskA-eval-%s|%d" % (what, seed))[:8], 16) / float(1 << 32)


def seat_of(seed):
    """이 seed 의 좌석 번호 (0~11)."""
    return (int(seed) * SEAT_STRIDE) % N_SEATS


def crate_shift(seed):
    """이 seed 의 바구니 옮김 (dx, dy), 월드 좌표 미터.

    옮기는 **크기**는 0 ~ `CRATE_SHIFT_M` 에서 고르게, 방향은 한 바퀴에서 고르게 뽑는다.

    **크기에 sqrt 를 씌우지 않는다.** 씌우면 원 넓이에 고르게 되어 큰 쪽으로 쏠린다 (15~20 mm 가
    44 %, 위 `CRATE_SHIFT_M` 머리말의 표). 원하는 것은 조금 옮기는 장면과 많이 옮기는 장면이 같은
    비율로 나오는 것이다.
    """
    seed = int(seed)
    r = CRATE_SHIFT_M * _unit(seed, "crate_r")
    th = 2.0 * math.pi * _unit(seed, "crate_th")
    return (float(r * math.cos(th)), float(r * math.sin(th)))


def spec(seed):
    """seed -> 장면 하나. **이 함수가 규칙의 전부다.**"""
    seed = int(seed)
    if seed < 0:
        raise ValueError("seed 는 0 이상이어야 한다 (받은 값 %d)" % seed)
    return {
        "seed": seed,
        "seat": seat_of(seed),
        "store_seed": _draw(seed, "store"),      # 기타 진열대
        "shelf_seed": _draw(seed, "shelf"),      # 목표 진열대
        "crate_shift_m": crate_shift(seed),      # 바구니 옮김 (dx, dy)
        "rule": ("seat=(seed*%d)%%%d, "
                 "store/shelf_seed=md5 추첨, "
                 "crate_shift=md5 추첨 반경 %.0f mm 안" % (SEAT_STRIDE, N_SEATS,
                                                       CRATE_SHIFT_M * 1000.0)),
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="seed 가 어떤 장면이 되는지 보여준다. Isaac Sim 을 안 띄운다.")
    ap.add_argument("--seed", type=int, nargs="*", default=[0, 1, 2, 1000],
                    help="볼 seed 들")
    ap.add_argument("--json", action="store_true", help="JSON 으로")
    a = ap.parse_args()

    out = [spec(s) for s in a.seed]
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    print("seed        좌석   매장씨앗   진열대씨앗   바구니 옮김 (mm)")
    for s in out:
        dx, dy = s["crate_shift_m"]
        print("%-10d  %2d   %8d   %8d     (%+6.1f, %+6.1f) = %4.1f"
              % (s["seed"], s["seat"], s["store_seed"], s["shelf_seed"],
                 dx * 1000.0, dy * 1000.0, math.hypot(dx, dy) * 1000.0))


if __name__ == "__main__":
    main()
