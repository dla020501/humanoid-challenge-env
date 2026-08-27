# Copyright 2025.
#
# 과제 A 의 열두 스폰 자세: 원형 시식 탁상 3 개, 탁상마다 좌석 4 개.
#
# 에피소드 하나는 로봇이 좌석 하나에 서고 그 앞 탁상에 바구니가 놓인 채로 시작한다. 이 모듈은
# 열둘 각각에 대해 로봇이 어디에 서고, 어디를 보고, 바구니가 어디에 놓이고, 이미 그 자리에
# 있던 스툴을 어떻게 하는지를 답한다.
#
# 이 파일은 대회 환경 저장소 `Task-A/sim/eatin_seats.py` 의 **배포용 정본**이다. 내용은
# 한 줄도 다시 쓰지 않았고, 바뀐 것은 실측값 파일을 찾는 자리 하나뿐이다 -- 배포 이미지에는
# `Task-A/` 가 없고 에셋은 `data/` 아래에 있다. 두 벌이 갈라지면 참가자가 보는 장면과
# 수집·채점이 쓰는 장면이 조용히 달라지므로, 값이 같은지는 추측할 것이 아니라 재야 한다:
#
#     python3 Task-A/sim/eatin_seats.py            # 원본이 내놓는 12 좌석
#     python3 -c "import taskA_seats; ..."          # 이 파일이 내놓는 12 좌석
#
# 참가자 저장소의 `scripts/task_a_demo.py --check` 가 그 대조를 한 번에 한다.
#
# 여기 있는 모든 크기는 `eatin_measured.json` 에서 읽는다. 그 파일은 `measure_eatin.py` 가
# 구워진 매장을 실제로 재서 만든 것이다. 아무것도 다시 적지 않는다. 이 모듈이 자라난 설계
# 메모는 세 숫자를 들고 있었는데 -- "스툴 반지름 0.62, 탁상 지름 ~1.14, 좌석은 45/135/225/315" --
# 재어 보니 앞의 둘이 문제가 될 만큼 틀렸다:
#
#   탁상 지름    1.0484 m, ~1.14 아님          (반지름 0.5242)
#   탁상 상판    0.7439 m
#   스툴 바닥면  반지름 0.1883 m               -- "0.62" 는 스툴 크기였던 적이 없다
#   스툴 거리    탁상 중심에서 0.6533 m        -- "0.62" 가 재고 있던 것이 이것이다
#
# 좌석 각도는 우리가 고르는 것이고 45/135/225/315 그대로다. 스툴은 지금 그 각도에 있지 않다:
# 매장은 `eatin_r` 키트로 지어지고(make_store.py:65) 그 키트는 스툴을 시드마다 다른 각도로
# 놓는다(21/92/159/325 등으로 실측). 그것을 정돈하는 것은 한 걸음이지 가정이 아니다.
#
# isaaclab 을 쓰지 않는 순수 파이썬이다. `zone_map.py`, `task_layout.py` 와 같은 이유다:
# 좌석 하나가 벽 안에 있다는 것을 알아내려고 시뮬레이터 기동 60 초를 치를 필요가 없다.
# 그리고 더 중요하게 -- isaaclab 이 SimulationApp 보다 먼저 import 되면 Isaac Sim 이 아예
# 뜨지 않는다. 데모 스크립트는 AppLauncher 앞에서 이 모듈을 읽는다.

import json
import math
import random
from pathlib import Path

# 실측값은 이 파일 **바로 옆**에 있다. 대회 환경 저장소에서는 `data/props/convstore/` 아래에
# 있었지만, 참가자 배포본에서는 모듈과 실측값이 함께 `scripts/taskA/` 에 산다 -- 둘 다 작고
# (4 KB), 둘이 떨어지면 어느 쪽이 낡았는지 알 길이 없기 때문이다.
MEASURED = Path(__file__).resolve().parent / "eatin_measured.json"

SEAT_ANGLES_DEG = (45.0, 135.0, 225.0, 315.0)

# The stools sit at random angles around the table -- scattered, but not free to land anywhere.
#
# Random because a tidy ring reads as a showroom rather than a shop, and these runs are training
# data for a vision model. Constrained because a stool in the seat is a stool the robot spawns
# inside: nothing can move once the run has started (authored USD transforms stop reaching the
# renderer the moment the stage is in Fabric -- measured 2026-08-12, twelve moves of up to 1.10 m
# written and every one ignored), so the arrangement has to be right before the simulation begins.
#
# The angle is free. What is constrained is the STRAIGHT-LINE DISTANCE from the stool to each of
# the four places a robot can stand, and that number is measured.
#
# An earlier version gave each stool its own 30-degree window centred between the seats. It worked
# but it always produced one stool per quadrant, evenly spaced -- a showroom, not a shop. Sampling
# the angle freely and rejecting the ones that come too close to a seat gives the same guarantee
# and lets two stools sit together with a gap elsewhere.
#
# Rejecting rather than pushing the stool outwards is not a preference. The robot stands 0.9242 m
# from the table centre, so clearing it by 0.55 m along the same direction would need a radius of
# 1.47 m -- a stool stranded in the middle of the floor, in the driving lane, beside a table of
# radius 0.5242. Inwards is no better: it would sit under the table top.
#
# !! 2026-08-13: THE MEASUREMENT BELOW IS SUSPECT AND HAS NOT BEEN REDONE.
# rotation_clearance.py placed the robot by writing a bare yaw over its root quaternion, which
# lays FFW-SG2 flat (90.0 degrees over, root 0.30 m up instead of 1.43). The placement is fixed
# now and the script asserts the tilt, but these numbers were taken before that and nobody has
# re-run them standing up. Treat 0.55 as provisional until the table is regenerated.
#
# WHERE 0.55 COMES FROM (rotation_clearance.py, 2026-08-12, table 0, all four seats)
#   stool 0.485 m away   turn completes in 2.6-3.2 s, base pushed <= 0.031 m -- same as open floor
#   stool 0.387 m away   two of four seats fail to finish 90 degrees in 5.9 s, pushed 0.152 m
# 0.469 m is where the two footprints touch (robot 0.281 + stool 0.1883), so the failure at 0.387
# is contact and nothing subtler. 0.55 sits above the distance that measured clean, with room for
# the base to shift while it turns.
STOOL_MIN_ROBOT_DIST = 0.55

# Stools also must not overlap each other: two footprints, plus a little, so they read as separate
# seats rather than one lump.
STOOL_MIN_PAIR_DIST_MARGIN = 0.06

# The band a stool's distance from the table centre is drawn from. Centred on the measured 0.6533
# so the arrangement still looks like seating at a table.
STOOL_DIST_JITTER = 0.06
STOOL_SEED = 20260812
STOOL_TRIES = 400

# How far the robot's centre must be from the table's EDGE.
#
# This is not a guess and not a margin picked to look comfortable -- it is the distance that was
# measured to still allow a turn on the spot. From task_layout.py:44-57: with the task-B table
# centred 0.90255 m ahead and 0.600 m deep, its face sat 0.60255 m from the robot's centre and the
# base turned -90.08 degrees against a -90 command. Pulling the table in so the face was 0.30255 m
# away -- 48 mm clear of the right swerve wheel at 0.2554 -- the same command achieved -0.61.
#
# That failure mode is fatal here specifically. The robot spawns facing the table and the first
# thing every episode does is turn, so a seat it cannot turn in deadlocks the episode at step one.
#
# !! 2026-08-13: SUSPECT, SAME REASON AS ABOVE -- the turn table below came from a run that may
# have had the robot on its side. Re-measure before relying on 0.40.
#
# 2026-08-12: pulled in from 0.60255 to 0.40, then MEASURED at the round table rather than
# inherited from the square one. rotation_clearance.py, table 0, all four seats, -90 commanded:
#
#   open floor (2.00 m)   100.5%   4.0 s   pushed 0.005 m      <- the control
#   0.60                  100%     2.5-2.8 s   <= 0.041 m
#   0.45                  100%     2.5-2.6 s   <= 0.024 m
#   0.40  (this value)    100%     2.6-3.2 s   <= 0.031 m      <- indistinguishable from open floor
#   0.35                  100%     2.6-4.5 s   <= 0.086 m      <- starting to touch
#   0.30                  100%     2.4-4.3 s   <= 0.091 m
#   0.25                  87.6% and 94.8% at two seats, 5.9 s spent, pushed 0.152 m
#
# So 0.40 is not a compromise between two square-table numbers, it is a distance at which the base
# turns as freely as it does on an empty floor. 0.35 is where contact begins and 0.25 is where the
# turn does not finish. Anything below 0.35 needs re-measuring, not reasoning.
FACE_CLEARANCE = 0.40

# Measured effective collision radius, wall face to robot centre (Task-A/CLAUDE.md).
ROBOT_RADIUS = 0.281


def _load():
    if not MEASURED.exists():
        raise FileNotFoundError(
            f"{MEASURED} 없음. 먼저 measure_eatin.py 를 돌려야 한다 -- 이 모듈은 크기를 "
            "추측하지 않는다.")
    return json.loads(MEASURED.read_text())


def geometry() -> dict:
    """The measured numbers the seat layout is built from."""
    m = _load()
    return {
        "table_radius": float(m["table_radius_max"]),
        "table_top_z": float(m["table_top_z_max"]),
        "stool_radius": float(m["stool_radius_max"]),
        "stool_dist": float(m["stool_dist_from_table"]),
        "standoff": float(m["table_radius_max"]) + FACE_CLEARANCE,
    }


# How wide an arc on the FAR side of the table the stools may occupy, measured from the direction
# directly opposite the robot. 90 means the whole far half.
#
# All four go behind the table, out of the robot's way. Scattering them around the whole rim --
# what this did until 2026-08-13 -- kept every stool 0.55 m from the robot's centre, which is
# enough not to overlap and NOT enough to drive between: two stools flanking the seat leave a gap
# narrower than the robot, and teleoperating it in was the thing that showed this. The far half is
# the only arrangement that leaves the approach completely clear.
STOOL_FAR_ARC_DEG = 80.0


def _idle_places(table_index: int, tx: float, ty: float, dist: float,
                 standoff: float, stool_radius: float, seed: int = 0) -> list:
    """Four (x, y) for a table the robot is NOT using -- scattered right round the rim.

    WHY THIS IS NOT `_stool_places` WITH ANOTHER SEAT NUMBER
      It used to be. `park_others` asked for each other table's SEAT-0 layout, and every table has
      the same four seat angles, so every idle table got its stools inside the same 80-degree
      window opposite seat 0. Three tables, one arrangement, repeated -- which the user spotted on
      screen (2026-08-18) and which is wrong twice over: the shop looks stamped out, and a policy
      learning from these pictures gets one stool arrangement instead of many.

      The far-side rule exists so the ROBOT CAN LEAVE ITS SEAT. It has no reason to apply to a
      table the robot never sits at, and applying it is what made them identical. So an idle table
      scatters over the whole circle, seeded per table so a re-run reproduces the picture and per
      episode so a fresh run does not.

    Still kept away from all twelve spawn poses: the robot does not sit here, but it drives past.
    """
    rng = random.Random(STOOL_SEED + table_index * 131 + seed * 7919)
    seats_xy = [(tx + standoff * math.cos(math.radians(a)),
                 ty + standoff * math.sin(math.radians(a))) for a in SEAT_ANGLES_DEG]
    pair_min = 2.0 * stool_radius + STOOL_MIN_PAIR_DIST_MARGIN
    out = []
    for _ in range(4):
        for _try in range(STOOL_TRIES):
            a = rng.uniform(-math.pi, math.pi)
            r = dist + rng.uniform(-STOOL_DIST_JITTER, STOOL_DIST_JITTER)
            x, y = tx + r * math.cos(a), ty + r * math.sin(a)
            if min(math.hypot(x - sx, y - sy) for sx, sy in seats_xy) < STOOL_MIN_ROBOT_DIST:
                continue
            if any(math.hypot(x - px, y - py) < pair_min for px, py in out):
                continue
            out.append((float(x), float(y)))
            break
        else:
            k = len(out)
            a = 2.0 * math.pi * k / 4.0 + 0.4
            out.append((float(tx + dist * math.cos(a)), float(ty + dist * math.sin(a))))
    return out


def _stool_places(table_index: int, seat_index: int, seat_angle: float,
                  tx: float, ty: float, dist: float,
                  standoff: float, stool_radius: float) -> list:
    """Four (x, y) stool positions, all on the far side of the table from this seat.

    Per SEAT, not per table: which side is "far" depends on where the robot stands, and one
    episode only ever uses one seat. Nothing can move once the simulation starts, so the layout is
    chosen for the seat the episode will use.
    """
    rng = random.Random(STOOL_SEED + table_index * 17 + seat_index)
    far = seat_angle + 180.0
    seats_xy = [(tx + standoff * math.cos(math.radians(a)),
                 ty + standoff * math.sin(math.radians(a))) for a in SEAT_ANGLES_DEG]
    pair_min = 2.0 * stool_radius + STOOL_MIN_PAIR_DIST_MARGIN

    out = []
    for _ in range(4):
        for _try in range(STOOL_TRIES):
            a = math.radians(far + rng.uniform(-STOOL_FAR_ARC_DEG, STOOL_FAR_ARC_DEG))
            r = dist + rng.uniform(-STOOL_DIST_JITTER, STOOL_DIST_JITTER)
            x, y = tx + r * math.cos(a), ty + r * math.sin(a)
            if min(math.hypot(x - sx, y - sy) for sx, sy in seats_xy) < STOOL_MIN_ROBOT_DIST:
                continue
            if any(math.hypot(x - px, y - py) < pair_min for px, py in out):
                continue
            out.append((float(x), float(y)))
            break
        else:
            k = len(out)
            a = math.radians(far - STOOL_FAR_ARC_DEG + 2 * STOOL_FAR_ARC_DEG * k / 3.0)
            out.append((float(tx + dist * math.cos(a)), float(ty + dist * math.sin(a))))
    return out


def seats(basket_inset: float = 0.20, stool_seed: int = 0) -> list:
    """The twelve spawn poses, in table-then-seat order.

    `basket_inset` is how far in from the table centre the basket sits, along the seat direction.

    0.20 and not 0.25, because the basket changed. The blue crate is 0.380 x 0.590 (taskB_table
    .CRATE_SIZE) and lies with its long side across the seat direction, so its far corner sits
    hypot(inset + 0.190, 0.295) from the table centre. Against a table radius of 0.5242 that is
    0.530 at an inset of 0.25 -- 6 mm over the edge -- and 0.489 at 0.20.

    Returns native floats only. numpy float64 makes Isaac Lab's float32 root-pose buffer raise
    `Index put requires the source and destination dtypes match` -- zone_map.sample_spawn was
    fixed for exactly this and the same care is owed here.
    """
    m = _load()
    g = geometry()
    out = []

    for s in m["sets"]:
        if "table" not in s:
            continue
        tx, ty = (float(v) for v in s["table"]["centre"])
        # Prim paths are taken from the measurement too, so a re-export that renames the kit is
        # caught by re-measuring rather than by a mystery at run time.
        stool_paths = [st["path"] for st in s.get("stools", [])]

        for k, ang in enumerate(SEAT_ANGLES_DEG):
            a = math.radians(ang)
            ca, sa = math.cos(a), math.sin(a)

            robot_x = tx + g["standoff"] * ca
            robot_y = ty + g["standoff"] * sa
            # Facing the table, i.e. back along the seat direction.
            robot_yaw = math.atan2(ty - robot_y, tx - robot_x)

            # Where the stools go: scattered inside their windows, at a jittered distance, all on
            # the far side of the table FROM THIS SEAT -- so the robot never has to drive through
            # them to leave. Measured 2026-08-18 on table 0: the four seats put their stools at
            # bearings centred on -135 / -45 / +45 / +135, each the seat angle plus 180.
            #
            # This comment used to say "the same four places for every seat of a table, which is
            # the point". That was wrong -- `_stool_places` takes `seat_index` and seeds on it, and
            # its own docstring says "Per SEAT, not per table". Nothing has to move mid-run because
            # an episode uses ONE seat, not because the layout is shared.
            #
            # Seeded per (table, seat) so a re-run reproduces the picture.
            tidy = _stool_places(int(s["index"]), k, ang, tx, ty, g["stool_dist"],
                                 g["standoff"], g["stool_radius"])
            # And where this table's stools stand when the robot is somewhere else. Same for all
            # four seats of a table, because it does not depend on which seat is unused.
            idle = _idle_places(int(s["index"]), tx, ty, g["stool_dist"],
                                g["standoff"], g["stool_radius"], seed=stool_seed)

            out.append({
                "table_index": int(s["index"]),
                "seat_index": int(k),
                "seat_angle_deg": float(ang),
                "table_xy": (float(tx), float(ty)),
                "robot_xy": (float(robot_x), float(robot_y)),
                "robot_yaw": float(robot_yaw),
                "basket_xyz": (float(tx + basket_inset * ca),
                               float(ty + basket_inset * sa),
                               float(g["table_top_z"])),
                "stool_paths": stool_paths,
                "stool_idle_xy": [(float(a), float(b)) for a, b in idle],
                "stool_tidy_xy": [(float(a), float(b)) for a, b in tidy],
            })

    return out


def check(store_x=(-11.1, 1.3), store_y=(-5.12, 7.25)) -> list:
    """Problems with the layout, as a list of strings. Empty means it is sound.

    Run before the simulator, not after: a seat inside a wall is cheap to find here and costs a
    minute of Isaac Sim startup to find there.
    """
    g = geometry()
    bad = []
    ss = seats()
    if len(ss) != 12:
        bad.append(f"좌석이 12개가 아니라 {len(ss)}개")

    for s in ss:
        x, y = s["robot_xy"]
        tag = f'table{s["table_index"]} seat{s["seat_index"]}'
        # Inside the store, with the robot's body accounted for.
        if not (store_x[0] + ROBOT_RADIUS <= x <= store_x[1] - ROBOT_RADIUS):
            bad.append(f"{tag}: x={x:.3f} 가 매장 밖(또는 벽에 닿음)")
        if not (store_y[0] + ROBOT_RADIUS <= y <= store_y[1] - ROBOT_RADIUS):
            bad.append(f"{tag}: y={y:.3f} 가 매장 밖(또는 벽에 닿음)")

        # The clearance the whole design rests on.
        face = math.hypot(x - s["table_xy"][0], y - s["table_xy"][1]) - g["table_radius"]
        if face < FACE_CLEARANCE - 1e-6:
            bad.append(f"{tag}: 탁상 면까지 {face:.3f} m < 회전 가능 최소 {FACE_CLEARANCE}")

        # The measured turn clearance, seat by stool. Not the overlap limit (0.469) -- 0.485 was
        # measured to turn cleanly and 0.387 to fail, so the test is the distance the stools were
        # placed to satisfy, checked here independently of the sampler that placed them.
        for j, (sx, sy) in enumerate(s["stool_tidy_xy"]):
            d = math.hypot(x - sx, y - sy)
            if d < STOOL_MIN_ROBOT_DIST - 1e-9:
                bad.append(f"{tag}: 스툴{j}까지 {d:.3f} m < 회전 실측 기준 {STOOL_MIN_ROBOT_DIST}")

        # The basket has to be on the table, not over its edge.
        bx, by, _ = s["basket_xyz"]
        if math.hypot(bx - s["table_xy"][0], by - s["table_xy"][1]) > g["table_radius"]:
            bad.append(f"{tag}: basket 이 탁상 밖")

    # Two robots never coexist, but two seats landing on the same spot would mean a bug.
    for i in range(len(ss)):
        for j in range(i + 1, len(ss)):
            if math.dist(ss[i]["robot_xy"], ss[j]["robot_xy"]) < 0.05:
                bad.append(f"좌석 {i}, {j} 가 같은 자리")

    return bad


if __name__ == "__main__":
    g = geometry()
    print("측정 기반 기하:")
    for k, v in g.items():
        print(f"  {k:14s} {v:.4f}")
    print()
    for s in seats():
        x, y = s["robot_xy"]
        print(f'  t{s["table_index"]} s{s["seat_index"]} '
              f'{s["seat_angle_deg"]:5.1f}deg  robot=({x:7.3f}, {y:7.3f}) '
              f'yaw={math.degrees(s["robot_yaw"]):7.1f}  '
              f'basket=({s["basket_xyz"][0]:7.3f}, {s["basket_xyz"][1]:7.3f})')
    print()
    problems = check()
    print("검증:", "문제 없음" if not problems else f"{len(problems)}건")
    for p in problems:
        print("   !", p)
