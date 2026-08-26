# Copyright 2025 ROBOTIS CO., LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""과제 B 의 시작 장면 하나를 띄워서 보여준다.

과제 B 는 "로봇이 가져온 상자에서 상품을 꺼내 진열대의 빈 칸에 놓는" 과제이고,
이 스크립트는 그 **에피소드가 시작되는 순간의 장면**을 만든다. 여기서 멈춘다 --
집지도, 놓지도, 움직이지도 않는다. 참가자가 보아야 하는 것은 자기 정책이 첫 관측으로
받게 될 바로 그 그림이기 때문이다.

한 장면은 seed 하나로 완전히 정해진다. 같은 seed 는 어디서 돌려도 같은 장면이다.

  * **진열대**  다섯 단이 상품으로 차 있고, 그 중 위 두 단(3단·2단)의 앞줄에서
    1~3 칸이 비어 있다. 비어 있는 칸 뒤에는 그 칸에 들어가야 할 상품이 서 있다 --
    "무엇을 채워야 하는가"는 진열대를 보면 읽을 수 있다.
  * **상자**    책상 위 파란 상자에 그 빈 칸 수만큼 상품이 들어 있다. i 번째 상품이
    i 번째 빈 칸에 들어간다.
  * **로봇**    진열대를 마주 보고, 바퀴가 바닥에 닿은 채로 선다. 공중에서 떨어지지
    않는다 -- 로봇 USD 의 정지 자세는 가장 낮은 바퀴를 218 mm 띄워 놓기 때문에,
    스폰 뒤 바퀴 높이를 재서 그만큼 내려 앉힌다(아래 settle_on_ground).

실행:

    cd /workspace/cyclo_lab
    ${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
        /workspace/challenge_scripts/task_b_demo.py --seed 1000

    # 화면 없이, 장면 내용만 파일로:
    ${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
        /workspace/challenge_scripts/task_b_demo.py --seed 1000 --headless \
        --seconds 2 --scene-json /workspace/user/scene_1000.json
"""

import argparse
import os

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="과제 B 의 시작 장면 하나를 띄운다.")
parser.add_argument("--seed", type=int, default=1000,
                    help="장면 하나를 정하는 수. 같은 값이면 같은 장면이다.")
parser.add_argument("--gaps", type=int, default=None, choices=(1, 2, 3),
                    help="빈 칸(=상자 속 상품) 개수. 기본값은 seed 가 정한다.")
parser.add_argument("--seconds", type=float, default=0.0,
                    help="장면을 몇 초 동안 유지할지. 0 이면 창을 닫을 때까지 (--headless "
                         "일 때는 1 초).")
parser.add_argument("--shot", default=None, metavar="FILE.png",
                    help="로봇 머리 카메라가 보는 그림을 한 장 저장한다. 화면 없이 돌릴 때 "
                         "장면을 눈으로 확인하는 길이고, 정책이 받게 될 관측 그대로다.")
parser.add_argument("--scene-json", default=None, metavar="FILE.json",
                    help="장면 내용을 JSON 으로 저장한다. 진열대 각 칸의 상품과 좌표, 빈 칸, "
                         "상자 속 상품이 들어 있다.")
AppLauncher.add_app_launcher_args(parser)
parser.set_defaults(device="cpu")     # 환경 하나뿐이라 GPU 파이프라인은 손해다 (1.83 ms vs 38.11)
args_cli = parser.parse_args()
args_cli.enable_cameras = True        # 로봇이 카메라를 달고 있어 이 깃발 없이는 스폰이 막힌다

import importlib.util as _ilu   # noqa: E402
import json                     # noqa: E402
import math                     # noqa: E402

CYCLOLAB = os.environ.get("CYCLOLAB_PATH", "/workspace/cyclo_lab")
_SRC = f"{CYCLOLAB}/source/cyclo_lab/cyclo_lab"
if not os.path.isdir(_SRC):
    raise SystemExit(f"환경 코드를 찾지 못했다: {_SRC}\n"
                     f"CYCLOLAB_PATH 를 확인하라 (현재 {CYCLOLAB!r}).")


def _by_path(name, path):
    """모듈을 경로로 읽는다.

    패키지(`import cyclo_lab`)를 거치면 isaaclab 이 딸려 들어오고, isaaclab 이
    SimulationApp 보다 먼저 import 되면 Isaac Sim 이 아예 뜨지 않는다. 아래 네 모듈은
    isaaclab 을 쓰지 않는 순수 파이썬이라 이렇게 먼저 읽을 수 있다.
    """
    spec = _ilu.spec_from_file_location(name, path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


taskB_shelf = _by_path("taskB_shelf", f"{_SRC}/assets/object/taskB_shelf.py")
taskB_restock = _by_path("taskB_restock", f"{_SRC}/assets/object/taskB_restock.py")
taskB_table = _by_path("taskB_table", f"{_SRC}/assets/object/taskB_table.py")
taskB_labels = _by_path("taskB_labels", f"{_SRC}/assets/object/taskB_labels.py")

# 진열대 앞면이 서는 x, 물리 한 걸음, 그리고 에피소드가 시작하는 몸통 높이·고개 각도.
# 모두 수집 코드가 쓰는 값 그대로다.
FRONT_X = 0.47
PHYSICS_DT = 1.0 / 120.0
START_LIFT = -0.05          # 진열대를 훑기 시작하는 몸통 높이
HEAD_TILT_DEG = 28.0        # 고개를 이만큼 숙이고 시작한다
SHOULDER_OUT_DEG = 20.0     # 팔을 몸에서 이만큼 벌린다 -- 0 이면 팔이 제 몸통 안에 박힌다
WHEEL_RADIUS = 0.0864       # 구동 바퀴 반지름 = 바퀴가 바닥에 닿았을 때의 바퀴 중심 높이


def straight_arm(side):
    """팔을 곧게 편 자세. 어깨만 몸 밖으로 20 도 벌리고 나머지 관절은 0.

    어깨 관절의 가동범위가 좌우 반대라서 부호가 갈린다(왼팔 +, 오른팔 -).
    """
    out = math.radians(SHOULDER_OUT_DEG) * (1.0 if side == "l" else -1.0)
    return (0.0, out, 0.0, 0.0, 0.0, 0.0, 0.0)


def draw_scene(seed, gaps):
    """이 seed 의 장면. Isaac 없이 정해지는 것 전부.

    돌려주는 것:
      shelf   [(상품명, 위치, 단, 칸)]  진열대에 서 있는 상품 전부
      gaps    [{layer, slot, product, label}]  비어 있는 칸과, 거기 들어가야 할 상품
      crate   [(상품명, 위치, 회전)]  상자 속 상품. i 번째가 gaps[i] 에 들어간다
      table / crate_pose  책상과 상자가 놓인 자리
    """
    n = (seed * 7919) % 3 + 1 if gaps is None else gaps
    # 이 두 모듈 전역이 곧 이 에피소드의 추첨 결과다. layout()/stock() 이 EPISODE_SLOTS 를,
    # product_poses() 가 CRATE_ITEMS 를 읽는다.
    taskB_restock.EPISODE_SLOTS = n
    columns, empty, items = taskB_restock.episode_layout(seed, n)
    taskB_table.CRATE_ITEMS = tuple(items)

    stocked = taskB_restock.stock(taskB_shelf.BOARD_TOPS, FRONT_X, seed)
    crate_pos, crate_rot = taskB_table.crate_pose(seed, fixed=True)
    crate = taskB_table.product_poses(seed, fixed=True)
    cols = taskB_restock.COLS

    return {
        "seed": seed,
        "gaps_n": n,
        "shelf": [(name, tuple(float(v) for v in pos),
                   taskB_restock.stock_orientation(name)[1], layer, slot)
                  for name, pos, layer, slot in stocked],
        "gaps": [{"layer": layer, "slot": slot, "col": slot % cols,
                  "product": columns[(layer, slot % cols)],
                  "label": taskB_labels.label(columns[(layer, slot % cols)])}
                 for layer, slot in empty],
        "crate": [(name, tuple(float(v) for v in pos), tuple(float(v) for v in rot))
                  for name, pos, rot in crate],
        "crate_pose": (tuple(float(v) for v in crate_pos),
                       tuple(float(v) for v in crate_rot)),
        "table_pose": taskB_table.table_pose(seed),
    }


def print_scene(scene):
    """장면을 사람이 읽을 수 있게 찍는다."""
    cols = taskB_restock.COLS
    print(f"\n[장면] seed {scene['seed']}, 빈 칸 {scene['gaps_n']} 개\n")
    print("  진열대 -- 단/줄/칸, 앞줄(row 0)이 손님 쪽")
    by_layer = {}
    for name, pos, _rot, layer, slot in scene["shelf"]:
        by_layer.setdefault(layer, []).append((slot, name, pos))
    for layer in sorted(by_layer, reverse=True):
        print(f"    {layer}단  (판 높이 {taskB_shelf.BOARD_TOPS[layer]:.3f} m)")
        for slot, name, pos in sorted(by_layer[layer]):
            print(f"      줄{slot // cols} 칸{slot % cols}  {taskB_labels.label(name):<28s}"
                  f"  ({pos[0]:+.3f}, {pos[1]:+.3f}, {pos[2]:.3f})  [{name}]")
    print("\n  비어 있는 칸 -- 상자 속 i 번째 상품이 i 번째 칸에 들어간다")
    for i, g in enumerate(scene["gaps"]):
        print(f"    {i}: {g['layer']}단 줄0 칸{g['col']}  <- {g['label']}  [{g['product']}]")
    print("\n  상자 속 상품")
    for i, (name, pos, _rot) in enumerate(scene["crate"]):
        print(f"    {i}: {taskB_labels.label(name):<28s}"
              f"  ({pos[0]:+.3f}, {pos[1]:+.3f}, {pos[2]:.3f})  [{name}]")
    (cx, cy, cz), _crot = scene["crate_pose"]
    print(f"\n  상자 {cx:+.3f}, {cy:+.3f}, {cz:.3f}"
          f"    책상 {scene['table_pose'][0][0]:+.3f}, {scene['table_pose'][0][1]:+.3f}"
          f"    진열대 앞면 x = {FRONT_X:.3f}\n")


SCENE = draw_scene(args_cli.seed, args_cli.gaps)
print_scene(SCENE)

if args_cli.scene_json:
    cols = taskB_restock.COLS
    with open(args_cli.scene_json, "w", encoding="utf-8") as fh:
        json.dump({
            "seed": SCENE["seed"],
            "shelf": [{"layer": layer, "row": slot // cols, "col": slot % cols,
                       "product": name, "label": taskB_labels.label(name),
                       "pos": [round(v, 5) for v in pos]}
                      for name, pos, _rot, layer, slot in SCENE["shelf"]],
            "gaps": SCENE["gaps"],
            "crate": [{"region": i, "product": name, "label": taskB_labels.label(name),
                       "pos": [round(v, 5) for v in pos]}
                      for i, (name, pos, _rot) in enumerate(SCENE["crate"])],
        }, fh, ensure_ascii=False, indent=2)
    print(f"[i] 장면을 {args_cli.scene_json} 에 적었다\n")

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import numpy as np                                                    # noqa: E402
import torch                                                          # noqa: E402
import isaaclab.sim as sim_utils                                      # noqa: E402
from isaaclab.assets import AssetBaseCfg, RigidObjectCfg              # noqa: E402
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg      # noqa: E402
from isaaclab.sensors import CameraCfg                                # noqa: E402
from isaaclab.utils import configclass                                # noqa: E402

from cyclo_lab.assets.robots.FFW_SG2 import (                         # noqa: E402
    FFW_SG2_MOBILE_CFG, SG2_SWERVE_STEERING_JOINTS, SG2_SWERVE_WHEEL_JOINTS,
)
from cyclo_lab.simulation_tasks.manager_based.manipulation.pick_place import (  # noqa: E402
    convstore_store,
)

LEFT_JOINTS = [f"arm_l_joint{i + 1}" for i in range(7)]
RIGHT_JOINTS = [f"arm_r_joint{i + 1}" for i in range(7)]


@configclass
class World(InteractiveSceneCfg):
    """바닥, 조명, 로봇, 진열대, 책상, 상자, 그리고 이 장면의 상품 전부.

    카메라 둘은 채점이 정책에게 보내는 관측과 같은 값이다 -- head_cam 672x376,
    right_wrist_cam 424x240. 환경 코드의 기본 해상도는 244x244 지만 채점 서버가
    이 값으로 덮어쓰므로, 여기도 같은 값을 명시한다. 왼손목 카메라는 현재 채점
    관측에 없다(스폰 자체를 안 한다).
    """

    ground = AssetBaseCfg(prim_path="/World/ground", spawn=sim_utils.GroundPlaneCfg())
    light = AssetBaseCfg(
        prim_path="/World/Light",
        spawn=sim_utils.DomeLightCfg(intensity=2500.0, color=(1.0, 1.0, 1.0)))
    robot = FFW_SG2_MOBILE_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")

    head_cam = CameraCfg(
        prim_path="{ENV_REGEX_NS}/Robot/ffw_sg2_follower/head_link2/head_cam",
        update_period=1.0e9, height=376, width=672, data_types=["rgb"],
        update_latest_camera_pose=True,
        spawn=sim_utils.PinholeCameraCfg(focal_length=12.0, focus_distance=400.0,
                                         horizontal_aperture=20.955,
                                         clipping_range=(0.1, 2.0)),
        offset=CameraCfg.OffsetCfg(pos=(-0.03, 0.04, 0.0), rot=(0.5, 0.5, -0.5, -0.5),
                                   convention="isaac"))
    right_wrist_cam = CameraCfg(
        prim_path="{ENV_REGEX_NS}/Robot/ffw_sg2_follower/arm_r_link7"
                  "/camera_r_bottom_screw_frame/camera_r_link/right_wrist_cam",
        update_period=1.0e9, height=240, width=424, data_types=["rgb"],
        update_latest_camera_pose=True,
        spawn=sim_utils.PinholeCameraCfg(focal_length=18.0, focus_distance=400.0,
                                         horizontal_aperture=20.955,
                                         clipping_range=(0.1, 2.0)),
        offset=CameraCfg.OffsetCfg(pos=(-0.08, 0.0, 0.0), rot=(0.5, -0.5, -0.5, 0.5),
                                   convention="isaac"))

    def __post_init__(self):
        self.shelf = taskB_shelf.taskB_shelf_cfg(FRONT_X)
        # 책상은 kinematic -- 과제 B 에서 로봇이 책상을 건드릴 일이 없고, 상자가 흔들리면
        # 상자 속 상품 좌표가 장면 기록과 어긋난다.
        tpos, trot = SCENE["table_pose"]
        self.table = AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/Table",
            spawn=sim_utils.UsdFileCfg(
                usd_path=taskB_table.TABLE_USD,
                rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True),
                collision_props=sim_utils.CollisionPropertiesCfg()),
            init_state=AssetBaseCfg.InitialStateCfg(pos=tpos, rot=trot))
        cpos, crot = SCENE["crate_pose"]
        self.crate = RigidObjectCfg(
            prim_path="{ENV_REGEX_NS}/Crate",
            spawn=sim_utils.UsdFileCfg(usd_path=taskB_table.CRATE_USD),
            init_state=RigidObjectCfg.InitialStateCfg(pos=cpos, rot=crot))
        # 진열대의 상품, 그 다음 상자의 상품. 한 상품이 여러 칸에 설 수 있으므로
        # prim 이름은 순번으로 짓는다.
        for i, (name, pos, rot, _layer, _slot) in enumerate(SCENE["shelf"]):
            setattr(self, f"shelf_item{i}",
                    convstore_store.product_cfg(f"ShelfItem{i}", name, pos, rot))
        for i, (name, pos, rot) in enumerate(SCENE["crate"]):
            setattr(self, f"crate_item{i}",
                    convstore_store.product_cfg(f"CrateItem{i}", name, pos, rot))


def main():
    sim = sim_utils.SimulationContext(
        sim_utils.SimulationCfg(dt=PHYSICS_DT, device=args_cli.device))
    scene = InteractiveScene(World(num_envs=1, env_spacing=8.0))
    sim.reset()

    robot = scene["robot"]
    names = list(robot.joint_names)
    left_ids, _ = robot.find_joints(LEFT_JOINTS, preserve_order=True)
    right_ids, _ = robot.find_joints(RIGHT_JOINTS, preserve_order=True)
    head_ids, _ = robot.find_joints(["head_joint1", "head_joint2"], preserve_order=True)
    lift_ids, _ = robot.find_joints(["lift_joint"], preserve_order=True)
    grip_ids, _ = robot.find_joints([f"gripper_{s}_joint{i + 1}"
                                     for s in ("l", "r") for i in range(4)],
                                    preserve_order=True)
    steer_ids, _ = robot.find_joints(list(SG2_SWERVE_STEERING_JOINTS), preserve_order=True)
    wheel_ids, _ = robot.find_joints(list(SG2_SWERVE_WHEEL_JOINTS), preserve_order=True)
    wheel_bodies = [i for i, n in enumerate(robot.body_names) if "wheel_drive_link" in n]

    left_hold = torch.tensor([list(straight_arm("l"))], device=sim.device)
    right_hold = torch.tensor([list(straight_arm("r"))], device=sim.device)
    head_hold = torch.tensor([[math.radians(HEAD_TILT_DEG), 0.0]], device=sim.device)
    lift_hold = torch.full((1, len(lift_ids)), START_LIFT, device=sim.device)
    zero_grip = torch.zeros((1, len(grip_ids)), device=sim.device)
    zero_steer = torch.zeros((1, len(steer_ids)), device=sim.device)
    zero_wheel = torch.zeros((1, len(wheel_ids)), device=sim.device)

    def hold(n):
        """n 걸음 동안 자세를 유지한다.

        바퀴 속도를 매 걸음 0 으로 눌러 준다 -- 마지막 속도 목표를 그대로 들고 있는
        바퀴는 계속 굴러간다.
        """
        for _ in range(n):
            robot.set_joint_position_target(left_hold, joint_ids=left_ids)
            robot.set_joint_position_target(right_hold, joint_ids=right_ids)
            robot.set_joint_position_target(head_hold, joint_ids=head_ids)
            robot.set_joint_position_target(lift_hold, joint_ids=lift_ids)
            robot.set_joint_position_target(zero_grip, joint_ids=grip_ids)
            robot.set_joint_position_target(zero_steer, joint_ids=steer_ids)
            robot.set_joint_velocity_target(zero_wheel, joint_ids=wheel_ids)
            scene.write_data_to_sim()
            sim.step(render=True)
            scene.update(PHYSICS_DT)

    def settle_on_ground():
        """로봇을 진열대 앞 제자리에, 바퀴를 바닥에 붙여 세운다.

        두 가지를 바로잡는다.

        1. **높이.** 로봇 USD 의 정지 자세는 가장 낮은 구동 바퀴를 0.3045 m 에 놓는다
           (실측 2026-08-12). 손대지 않으면 로봇은 218 mm 를 낙하한다 -- "스폰할 때
           위에서 떨어진다"가 그것이다. 그래서 실제 바퀴 높이를 재고 그 차이만큼 루트를
           내린다. 설정값을 218 mm 낮추는 것으로는 안 된다: 이 관절 구조에는 몸체 변환이
           어긋난 FixedJoint 가 있어 오프셋이 1:1 로 전달되지 않고(바퀴가 0.1672 로
           나왔다), 그러면 차체가 무언가와 겹쳐 PhysX 가 로봇을 1.34 m 로 던진다.

        2. **자리.** 낙하는 로봇을 옆으로도 밀어 놓는다(실측: x 가 -22.6 mm). 이 데모는
           환경을 보여 주는 것이므로 설정된 자리에 똑바로 세운다. 시연 수집 쪽은 일부러
           이 보정을 하지 않는다 -- 거기서는 "튄 자리"가 곧 그 에피소드의 시작 자세다.
        """
        want = robot.data.default_joint_pos[0].clone()
        want[names.index("head_joint1")] = math.radians(HEAD_TILT_DEG)
        want[names.index("lift_joint")] = START_LIFT
        robot.write_joint_state_to_sim(want.unsqueeze(0), torch.zeros_like(want).unsqueeze(0))
        scene.write_data_to_sim()
        home = FFW_SG2_MOBILE_CFG.init_state.pos
        upright = torch.as_tensor(np.asarray(FFW_SG2_MOBILE_CFG.init_state.rot,
                                             dtype=np.float32), device=sim.device)
        for _ in range(2):
            hold(1)
            low = min(float(robot.data.body_pos_w[0, i][2]) for i in wheel_bodies)
            st = robot.data.root_state_w[0].clone()
            st[0] = float(home[0])
            st[1] = float(home[1])
            st[2] -= low - WHEEL_RADIUS
            st[3:7] = upright
            st[7:] = 0.0
            robot.write_root_state_to_sim(st.unsqueeze(0))
            scene.write_data_to_sim()
        return min(float(robot.data.body_pos_w[0, i][2]) for i in wheel_bodies)

    settle_on_ground()

    def rewrite_products():
        """상품을 제 좌표에 다시 적는다. 속도는 0 으로.

        순간이동으로 놓인 상품은 접촉을 찾느라 1~2 mm 씩 기어간다. 가라앉은 뒤
        한 번 더 적어야 장면이 '기록된 좌표 근처'가 아니라 '기록된 좌표'가 된다.
        """
        for i, (_n, pos, rot, _l, _s) in enumerate(SCENE["shelf"]):
            _set_root(scene[f"shelf_item{i}"], pos, rot)
        for i, (_n, pos, rot) in enumerate(SCENE["crate"]):
            _set_root(scene[f"crate_item{i}"], pos, rot)
        _set_root(scene["crate"], *SCENE["crate_pose"])
        scene.write_data_to_sim()

    def _set_root(obj, pos, quat):
        st = obj.data.root_state_w[0].clone()
        st[:3] = torch.as_tensor(np.asarray(pos, dtype=np.float32), device=st.device)
        st[3:7] = torch.as_tensor(np.asarray(quat, dtype=np.float32), device=st.device)
        st[7:] = 0.0
        obj.write_root_state_to_sim(st.unsqueeze(0))

    hold(int(1.5 / PHYSICS_DT))
    rewrite_products()
    hold(int(0.5 / PHYSICS_DT))

    x, y = float(robot.data.root_pos_w[0][0]), float(robot.data.root_pos_w[0][1])
    q = robot.data.root_quat_w[0]
    w, qx, qy, qz = (float(v) for v in q)
    yaw = math.degrees(math.atan2(2.0 * (w * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz)))
    low = min(float(robot.data.body_pos_w[0, i][2]) for i in wheel_bodies)
    print(f"[i] 로봇 시작 자세  x {x:+.4f}  y {y:+.4f}  yaw {yaw:+.2f} deg"
          f"  몸통 {float(robot.data.joint_pos[0, lift_ids[0]]):+.4f}", flush=True)
    print(f"[i] 가장 낮은 바퀴 {low:.4f} m -- 바퀴 반지름 {WHEEL_RADIUS:.4f} 이므로 "
          f"바닥에 닿아 있다 (공중에서 떨어지지 않았다)", flush=True)
    print("[i] 장면이 섰다. 여기서 과제 B 가 시작한다.\n", flush=True)

    if args_cli.shot:
        cam = scene["head_cam"]
        # 카메라는 update_period 가 커서 스스로 갱신하지 않는다. 한 장을 원하면 낡았다고
        # 표시하고 강제로 다시 그리게 한다.
        cam._is_outdated[:] = True
        cam.update(PHYSICS_DT, force_recompute=True)
        rgb = cam.data.output["rgb"][0][..., :3].cpu().numpy().astype(np.uint8)
        from PIL import Image
        Image.fromarray(rgb).save(args_cli.shot)
        print(f"[i] 머리 카메라 그림을 {args_cli.shot} 에 적었다 "
              f"({rgb.shape[1]}x{rgb.shape[0]})\n", flush=True)

    secs = args_cli.seconds or (1.0 if args_cli.headless else 0.0)
    if secs > 0.0:
        hold(int(secs / PHYSICS_DT))
    else:
        while simulation_app.is_running():
            hold(1)


main()
simulation_app.close()
