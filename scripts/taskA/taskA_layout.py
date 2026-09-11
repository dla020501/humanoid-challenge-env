# Copyright 2025.
#
# 과제 A 한 에피소드의 자리들: 로봇이 어디에 서서 시작하는지, 바구니를 어디로 가져가야
# 하는지, 그 옆 책상이 어디에 있는지.
#
# 에피소드 하나는 시식 탁상에서 바구니를 집어 -> 장애물을 피해 목적지 진열대까지 몰고 ->
# 그 옆 책상 위에 내려놓는 것이다. 좌석과 바구니는 `taskA_seats.py` 가, 목적지와 책상은
# 이 파일이 답한다.
#
# 이 파일은 대회 환경 저장소 `Task-A/sim/task_layout.py` 에서 **데모가 쓰는 부분만** 옮긴
# 것이다. 원본은 옛 정의(매장 어디서나 스폰하고 그 앞에 탁상을 놓던)를 위한 함수들도 함께
# 들고 있는데, 지금 정의에서 로봇이 서는 탁상은 매장 USD 안에 이미 있는 시식 탁상이라
# 그 함수들은 쓰이지 않는다. 옮기지 않은 것을 여기 적어 둔다 -- `spawn_table_pose`,
# `basket_on_table_pose`, `episode_props`, `desk_box`, 그리고 주행 중 머리 동작(`HEAD_LOOK`).
#
# 숫자는 복사하지 않는다. 책상과 바구니의 USD 경로와 실측 치수는 `taskB_table.py` 가 이미
# 들고 있고, 목적지와 책상 자리는 `destinations.json` 이 들고 있다. 둘 다 읽어서 쓴다 --
# 같은 값을 두 번째로 적어 두는 것은 두 값이 갈라질 두 번째 기회다.
#
# isaaclab 을 쓰지 않는 순수 파이썬이다. 데모 스크립트가 AppLauncher 보다 먼저 이 모듈을
# 읽는데, isaaclab 이 SimulationApp 보다 먼저 import 되면 Isaac Sim 이 아예 뜨지 않는다.

import importlib.util as _ilu
import json as _json
import math as _math
import os as _os

_HERE = _os.path.dirname(_os.path.abspath(__file__))

# 이 모듈이 읽는 것은 두 자리에 나뉘어 있고, 나뉜 이유가 있다.
#
#   목적지·좌석 실측값  이 파일 바로 옆 (`scripts/taskA/`). 합쳐서 6 KB 이고, 모듈과 함께
#                      `git pull` 로 갱신된다.
#   매장 USD           배포 이미지 안. 184 MB 라 저장소에 둘 물건이 아니고, 참조 94 개와
#                      텍스처 180 장을 상대경로로 물고 있어 통째로 옮겨야 한다.
#
# 이미지 안 자리는 데모 스크립트와 같은 방식으로 찾는다.
_CYCLOLAB = _os.environ.get("CYCLOLAB_PATH", "/workspace/cyclo_lab")
_IMAGE_DATA = f"{_CYCLOLAB}/source/cyclo_lab/data"

# --------------------------------------------------------------------------- 매장
#
# 매장 전체가 담긴 USD 하나. `fixture_kit/make_store.py` 가 조립한 것이고, 참조 94 개와
# 텍스처 180 장이 전부 **상대경로**로 걸려 있어 통째로 옮겨도 끊기지 않는다.
#
# 왜 `convstore_store.py` 로 매장을 짓지 않고 이 USD 를 통째로 참조하는가:
#
#   매장 배치가 바뀌었다 -- 통로 1.52 -> 1.85 m, 곤돌라 세 번째 열, 시식 코너 추가,
#   아이스크림 냉동고 제거. 그런데 그 변경은 `fixture_kit/make_store.py` 에만 있고
#   시뮬레이션 태스크가 읽는 `convstore_store.py` 에는 없다. 그쪽으로 옮기면 과제 B 와
#   과제 C 의 장면까지 함께 바뀌는데, 그것은 과제 A 가 할 일이 아니다. 이 파일을 참조하면
#   공유 코드를 한 줄도 건드리지 않고 새 매장을 얻는다.
#
#   이 USD 의 상품들은 보이기만 하고 콜라이더가 없다(fixture_kit 의 의도된 설계). 주행
#   과제에는 오히려 이득이다 -- 넘어뜨릴 것이 없고, 물건이 떨어져 에피소드가 중단될 일도 없다.
#
# 집기들의 콜라이더는 꺼진 채로 실려 오므로 `taskA_colliders.harden()` 이 켜 준다.
STORE_USD = f"{_IMAGE_DATA}/store/scene/fixture_kit/out/store_scene.usd"

# 매장의 범위 (x, y). `taskA_seats.check()` 가 좌석이 벽 안쪽인지 볼 때 쓴다.
STORE_X = (-11.1, 1.3)
STORE_Y = (-5.12, 7.25)


def _load(name, filename):
    """**이미지 안** 과제 B 모듈을 경로로 읽는다.

    `import cyclo_lab...` 로 가면 패키지 __init__ 사슬이 isaaclab 을 끌고 들어온다.
    taskB_table.py 자신이 taskB_restock 을 읽을 때 쓰는 것과 같은 방법이다.

    **왜 옆에 복사해 두지 않는가.** 이 파일 머리말이 적었듯 "같은 값을 두 번째로 적어 두는
    것은 두 값이 갈라질 두 번째 기회" 다. taskB_table.py 는 과제 B 의 것이고 책상·바구니의
    치수와 USD 경로를 들고 있다. 사본을 두면 과제 B 가 그 값을 고칠 때 과제 A 만 낡는다.
    """
    spec = _ilu.spec_from_file_location(
        name, f"{_CYCLOLAB}/source/cyclo_lab/cyclo_lab/assets/object/{filename}")
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


taskB_table = _load("_taskA_taskB_table", "taskB_table.py")

# --------------------------------------------------------------------------- 바구니
#
# data/Crate 의 파란 상자. 2026-08-12 에 사용자가 과제 B 에서 빌려 쓰던 보라색 것 대신
# 이것으로 정했다. taskB_table.py 가 0.380 x 0.590 x 0.140, 밑면이 z = 0 이라고 적고
# 있고 아래 숫자는 거기서 온다 -- 하나도 다시 적지 않는다.
BASKET_USD = taskB_table.CRATE_USD
BASKET_SIZE = taskB_table.CRATE_SIZE

# 이 에셋은 원점이 곧 밑면이라 0 이다. z 를 탁상 상판에 맞추면 그대로 탁상 위에 놓인다.
# 앞선 바구니 둘은 여기에 보정이 필요했고 이유도 서로 달랐다(하나는 최저 지오메트리보다
# 3.61 mm 위에 원점이 있었고, 다른 하나는 아니었다). 그래서 맨 상수가 아니라 "어느 에셋을
# 쓰는가" 에 걸린 식으로 남긴다 -- 다음에 에셋이 바뀔 때 조용히 틀리지 않도록.
BASKET_ORIGIN_LIFT = 0.0 if BASKET_USD == taskB_table.CRATE_USD else None

# --------------------------------------------------------------------------- 책상
#
# 목적지 진열대 옆의 과제 B 책상. **그 자리는 사용자의 것이다.**
#
# taskB_table.py 가 그렇게 적고 있다 -- 그 자리는 묻지 않고 다시 고를 것이 아니다 -- 그래서
# 여기서 다시 유도하지 않고, 우리 매장 좌표계로 옮겨진 값을 읽기만 한다:
#
#   과제 B 좌표계   진열대 앞면 x 0.470, 진열대는 y -0.45..+0.45,  책상 (-0.28182, -0.90255)
#   우리 매장       진열대 앞면 x 0.913, 진열대는 y  2.150..3.050
#   따라서          x +0.443, y +2.600   ->   (0.1616, 1.6975)
DESK_USD = taskB_table.TABLE_USD
DESK_SIZE = taskB_table.TABLE_SIZE

# 어디에 서는지는 destinations.json 이 말한다. 그 파일이 유일한 출처다.
#
# 2026-08-20 이전에는 책상 자리가 코드에, 로봇이 가서 서는 자리가 destinations.json 에,
# 그리고 세 번째로 목표 진열대의 바운딩 박스에서 다시 유도하는 함수에 있었다. 셋은 갈라져
# 있었고, 그래서 수집기는 한 자리로 몰고 가서 실제로 스폰된 것과 0.198 m 떨어진 책상을
# 향해 놓으려 했다. 아래 literal 은 그 파일이 없는 체크아웃을 위한 대비값이고, 값은
# 반드시 서로 같아야 한다.
# **z 는 0 이 아니라 매장 충돌 바닥의 높이다.**
#
# 매장 바닥은 세 겹이고 로봇과 가구가 실제로 타는 면은 z = +0.002 다 (실측 2026-08-17,
# `Task-A/CLAUDE.md` 9 절: 매장 충돌 바닥 +0.002000 / 보이는 바닥 +0.000245 / GroundPlane 0).
# 여기 0.0 을 두면 책상이 그 면보다 2 mm 아래에 못 박히고, 바닥에 **박힌** 채로 선다.
#
# 그게 왜 점수를 바꾸는가: 바구니가 책상을 따라 2 mm 낮게 앉는데 채점기의 기준면은 안 따라
# 내려가서, 정상적인 놓기가 「얹힘 아님」-> 「낙하」로 찍혔다 (참가자 이슈 #3, 2026-09-10).
#
# **과제 B 와 같은 규칙이다.**  `taskB_table.TABLE_POS = (..., 0.0)` 이고 과제 B 의 세계는
# 맨 GroundPlane(z = 0)이라 그 0.0 이 곧 바닥 높이다 (`task_b_demo.py:243`).  규칙은
# 「책상 원점 = 바닥 높이」이고, 우리 바닥이 +0.002 이므로 우리 값은 0.002 다.  과제 B 의
# **숫자**를 베끼면 그 바닥에서만 맞는 값을 베끼는 것이 된다.
#
# 수집기가 이미 이렇게 한다 -- `Task-A/sim/props.py` 는 책상을 동적 강체로 띄워 **가라앉혀**
# 세우고, 그 결과가 시연 세 편에 `desk_pos.z = 0.002000391` 로 기록돼 있다 (실측 바닥과
# 0.4 마이크로미터 차이).  끝자리 391 이 그 증거다 -- 설정한 상수라면 딱 떨어진다.
DESK_POS = (0.1616, 1.6975, 0.002)
GOAL_POSE = (-0.1003, 2.5588, 0.0)

_DESTINATIONS = _os.path.join(_HERE, "destinations.json")


def _real_destination():
    """destinations.json 의 **진짜** 목적지 한 줄. 없으면 None.

    가짜 목적지(하드 네거티브)는 건너뛴다. 참가자 환경은 진짜 하나만 세운다 -- 수집 때
    쓰는 가짜 진열대·가짜 책상은 학습 데이터를 만들기 위한 것이지 장면의 일부가 아니다.
    """
    try:
        with open(_DESTINATIONS, encoding="utf-8") as fh:
            rows = _json.load(fh)["destinations"]
    except (OSError, ValueError, KeyError):
        return None
    for r in rows:
        if not r.get("fake"):
            return r
    return None


def goal_pose():
    """로봇이 도착해서 서는 자리 (x, y, yaw). 목적지 진열대를 마주 본다."""
    r = _real_destination()
    if r is None:
        return GOAL_POSE
    return (float(r["x"]), float(r["y"]), float(r.get("yaw", 0.0)))


def desk_pos():
    """바구니를 내려놓는 책상의 중심 (x, y, z). z 는 바닥이다."""
    r = _real_destination()
    if r is None or not r.get("desk_xy"):
        return DESK_POS
    return (float(r["desk_xy"][0]), float(r["desk_xy"][1]), DESK_POS[2])


def desk_top_z():
    """책상 상판의 **월드 높이**. 바구니는 여기에 놓인다.

    **원점 + 높이다.  높이만 돌려주면 안 된다.**

    앞 판은 `float(DESK_SIZE[2])` 였다 -- 그것은 책상의 **치수**(0.725 m)이지 상판이 있는
    월드 z 가 아니다.  책상 원점이 0 일 때만 우연히 같아지고, 원점이 움직이는 순간 조용히
    틀린다.  채점기가 이 값을 기준면으로 쓰므로 그 오차가 곧 점수가 된다 (이슈 #3).

    **과제 B 는 처음부터 이렇게 하고 있었다:**

        taskB_table.py:101-103
            TABLE_POS  = (-0.28182, -0.90255, 0.0)
            TABLE_SIZE = (0.600, 0.600, 0.725)
            TABLE_TOP  = TABLE_POS[2] + TABLE_SIZE[2]

    같은 에셋·같은 치수를 가져오면서 `+ TABLE_POS[2]` 항만 빠뜨렸다.  여기서 되돌린다.
    """
    return float(DESK_POS[2] + DESK_SIZE[2])


# 목적지에서 책상까지의 거리. 2026-08-21 에 목적지를 책상에서 0.682 -> 0.900 m 로 물렸다.
# 0.682 m 에서는 제자리 회전이 로봇 뒤 모서리를 책상 바닥판에 41.9 mm 밀어 넣었다
# (베이스 커버는 앞뒤 -0.403..+0.225 m, 좌우 +-0.301 m 라 뒤 모서리가 중심에서 0.503 m).
# 0.900 m 면 가장 나쁜 방향에서도 166 mm 가 남는다.
DESK_SIDE_D = 0.90

# --------------------------------------------------------------------------- 시작 자세
#
# 에피소드가 시작되는 순간의 로봇. 좌석에서 300 mm 앞으로 나와, 몸통을 이미 작업 높이까지
# 내리고, 고개를 숙이고, 팔은 집기 직전 모양을 하고 있다.
#
# 값은 조작자의 것이다 -- teleop GUI 에서 손으로 잡고 18:17:06 에 저장된 take 에서 읽어냈다.
# 명령값이지 도달값이 아니다: 시작 자세란 "어디에 있으라고 했는가" 이지 "컨트롤러가 어디까지
# 갔는가" 가 아니다.
#
# 이것이 한곳에 있는 이유: teleop 도구와 경로계획이 서로 갈라져 있다가 2026-08-15 에야
# 발각됐다. teleop 은 좌석에서 300 mm 앞에 팔을 든 채로 스폰했고, 경로계획은 174 mm 와 옛
# 홈 자세를 가정했다. 팔 관절 14 개 중 8 개가 최대 22 도씩 달랐다.
SPAWN_FORWARD = 0.300              # 좌석에서 앞으로 이만큼. 탁상 중심에서 0.924 - 0.300 = 0.624 m
SPAWN_LIFT = -0.0600               # 몸통은 이미 작업 높이에 내려와 있다
SPAWN_HEAD_PITCH = 0.6946          # 양수가 아래. 한계는 0.6951 -- 39.8 도 숙인다
SPAWN_HEAD_YAW = 0.0
SPAWN_ARM_L = (0.3840, 0.1745, 0.0000, -1.8151, 0.1396, 0.0, 0.0)
SPAWN_ARM_R = (0.3840, -0.1745, 0.0000, -1.8151, -0.1047, 0.0, 0.0)


def spawn_arm_pos(side):
    """`side` 는 "l" 또는 "r". 손목(joint6, joint7)은 양팔 모두 0 -- 굽히지도 비틀지도 않는다."""
    return SPAWN_ARM_L if side == "l" else SPAWN_ARM_R


def spawn_robot_pose(seat):
    """`taskA_seats.seats()` 의 좌석 하나를 받아 로봇의 시작 (x, y, yaw).

    좌석 자체(탁상 중심에서 0.9242 m)가 아니라 거기서 바라보는 방향으로 SPAWN_FORWARD 만큼
    나온 자리다. 그 자리는 탁상 반경(0.5242) + 로봇 반경(0.281) = 0.805 보다 안쪽인
    0.624 m 이므로 **로봇은 여기서 제자리 회전을 할 수 없다.** 팔만 움직이는 동안에는
    상관없고, 집은 뒤에는 먼저 후진해서 빠져나온 다음 돌아야 한다(2026-08-17 실측: 50 초
    동안 좌회전을 명령했는데 명령 회전율의 2 % 만 나왔고 탁상 주위를 미끄러졌다).
    """
    yaw = float(seat["robot_yaw"])
    x, y = seat["robot_xy"]
    return (float(x) + SPAWN_FORWARD * _math.cos(yaw),
            float(y) + SPAWN_FORWARD * _math.sin(yaw),
            yaw)
