# Copyright 2026 ROBOTIS CO., LTD.
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

"""과제 C 시연 기록 한 판을 물리로 다시 튼다.

`task_c_demo.py` 는 **시작 장면**을 세우고 멈춘다. 이 스크립트는 그 다음을 보여준다 --
로봇이 계산대의 상품을 집어 스캐너에 비추고 제자리에 내려놓는 한 판이다. 상품 3개를
차례로 처리하는 판(정답 궤적, `--set gt`)과 상품 하나만 처리하는 판(학습 데이터와 같은
형식, `--set single`)이 있다.

    cd /workspace/cyclo_lab
    ${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
        /workspace/challenge_scripts/task_c_replay.py --set gt --seed 0

**이것은 물리 재생이다.** 기록에는 로봇에게 준 관절 명령(`actions.npy`, 22 차원, 30 Hz)과
실측 관절값(`joints.npy`)만 있고 상품의 자세는 없다. 그래서 상품을 프레임마다 놓는 대신,
기록된 관절 명령을 그때와 같은 주기로 로봇에게 다시 주고 **물리가 상품을 움직이게 한다.**
물리가 결정적이라 시작 장면이 같으면 상품이 그때처럼 손에 딸려 오고, 스캐너 앞을 지나고,
띠 안에 놓인다. 접촉이 실제로 일어나므로 "이 파지가 버티는가" 도 화면이 답한다.

기록은 30 Hz(물리 120 Hz 의 4 걸음마다 한 프레임)다. 재생은 프레임 사이를 물리 4 걸음으로
잇고, 이웃 프레임 사이의 명령을 선형으로 채운다(`--no-interp` 로 끌 수 있다).

    --set gt|single       어느 묶음 (기본 gt)
    --seed N              그 묶음의 몇 번째 판 (--list 로 목록)
    --episode DIR         묶음 대신 기록 폴더를 직접 준다 (joints/actions/timestamps.npy + 장면 JSON)
    --substeps 4          기록 한 프레임을 물리 몇 걸음으로 잇나 (기록과 같은 4 가 실제 속도)
    --frames N            앞에서 N 프레임만 튼다 (0 이면 전부)
    --list                들어 있는 판을 찍고 끝낸다
"""

import argparse
import glob
import json
import os
import sys
import threading as _threading

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="과제 C 시연 기록 한 판을 물리로 다시 튼다.")
parser.add_argument("--set", default="gt", choices=["gt", "single"],
                    help="gt = 상품 3개 연속 정답 궤적, single = 상품 하나 시연 (기본 gt)")
parser.add_argument("--seed", type=int, default=0, help="어느 판을 틀지. --list 로 목록을 본다.")
parser.add_argument("--episode", default=None, metavar="DIR",
                    help="묶음 대신 기록 폴더를 직접 준다.")
parser.add_argument("--substeps", type=int, default=4,
                    help="기록 한 프레임을 물리 몇 걸음으로 잇나. 4 가 기록과 같은 속도.")
parser.add_argument("--no-interp", action="store_true", help="이웃 프레임 사이 명령을 채우지 않는다.")
parser.add_argument("--frames", type=int, default=0, help="앞에서 N 프레임만 튼다 (0 = 전부).")
parser.add_argument("--start-hold", type=float, default=1.0,
                    help="첫 프레임 자세로 몇 초 세워 둔 뒤 시작하나 (상품 정착 시간).")
parser.add_argument("--summary-json", default=None, metavar="FILE.json",
                    help="재생 결과 요약(상품 이동·들림·스캐너 접근·최종 자리)을 JSON 으로 저장한다.")
parser.add_argument("--list", action="store_true", help="들어 있는 판을 찍고 끝낸다.")
AppLauncher.add_app_launcher_args(parser)
parser.set_defaults(device="cpu")
args_cli = parser.parse_args()
args_cli.enable_cameras = True

import importlib.util as _ilu   # noqa: E402
import math                     # noqa: E402

CYCLOLAB = os.environ.get("CYCLOLAB_PATH", "/workspace/cyclo_lab")
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from taskC import taskC_check as K        # noqa: E402
from taskC import taskC_layout as L       # noqa: E402
from taskC import taskC_products as P     # noqa: E402

DEMO_DIRS = {"gt": os.path.join(_HERE, "taskC", "demos_gt"),
             "single": os.path.join(_HERE, "taskC", "demos")}
PHYSICS_DT = 1.0 / 120.0
RENDER_EVERY = 4
WHEEL_RADIUS = L.WHEEL_RADIUS
STORE_USD = str(P.store_usd())
SCANNER_USD = str(P.scanner_usd())

# 기록의 22 열. kit_config.STATE_JOINTS 와 같다: 왼팔 7 · 왼 그리퍼 1 · 오른팔 7 · 오른 그리퍼 1 ·
# 머리 2 · 리프트 1 · 예비 3(베이스 속도 -- 정지 과제라 0).
REC_JOINTS = ([f"arm_l_joint{i}" for i in range(1, 8)] + ["gripper_l_joint1"]
              + [f"arm_r_joint{i}" for i in range(1, 8)] + ["gripper_r_joint1"]
              + ["head_joint1", "head_joint2", "lift_joint"])


def _demos(which):
    out = []
    for d in sorted(glob.glob(os.path.join(DEMO_DIRS[which], "*"))):
        if os.path.isfile(os.path.join(d, "actions.npy")) or os.path.isfile(os.path.join(d, "joints.npy")):
            out.append(d)
    return out


def _meta(d):
    f = os.path.join(d, "meta.json")
    return json.load(open(f, encoding="utf-8")) if os.path.isfile(f) else {}


if args_cli.list or (args_cli.episode is None):
    lst = _demos(args_cli.set)
    if args_cli.list:
        for which in ("gt", "single"):
            print(f"\n[{which}] {DEMO_DIRS[which]}")
            for i, d in enumerate(_demos(which)):
                m = _meta(d)
                order = m.get("chain_order") or [m.get("slug", "?")]
                print(f"  --seed {i}: {os.path.basename(d):<32s} {' -> '.join(order)}")
        raise SystemExit(0)
    if not lst:
        raise SystemExit(f"판이 하나도 없다: {DEMO_DIRS[args_cli.set]}")
    if not 0 <= args_cli.seed < len(lst):
        raise SystemExit(f"--seed 는 0..{len(lst) - 1} (--list 로 목록을 보라)")
    EPISODE = lst[args_cli.seed]
else:
    EPISODE = args_cli.episode
if not os.path.isdir(EPISODE):
    raise SystemExit(f"기록 폴더가 없다: {EPISODE}")

import numpy as np  # noqa: E402

ACT_FILE = os.path.join(EPISODE, "actions.npy")
JNT_FILE = os.path.join(EPISODE, "joints.npy")
if not os.path.isfile(ACT_FILE) and not os.path.isfile(JNT_FILE):
    raise SystemExit(f"actions.npy 도 joints.npy 도 없다: {EPISODE}")
ACTIONS = np.load(ACT_FILE) if os.path.isfile(ACT_FILE) else np.load(JNT_FILE)
JOINTS = np.load(JNT_FILE) if os.path.isfile(JNT_FILE) else ACTIONS
TS = np.load(os.path.join(EPISODE, "timestamps.npy")) if os.path.isfile(os.path.join(EPISODE, "timestamps.npy")) else None
if ACTIONS.shape[1] < len(REC_JOINTS):
    raise SystemExit(f"기록 열이 {ACTIONS.shape[1]} 개다 -- {len(REC_JOINTS)} 개(22 차원 규약)여야 한다")
_scene_files = sorted(glob.glob(os.path.join(EPISODE, "taskC_qr_scene_*.json"))) + \
    ([os.path.join(EPISODE, "scene.json")] if os.path.isfile(os.path.join(EPISODE, "scene.json")) else [])
if not _scene_files:
    raise SystemExit(f"장면 JSON(taskC_qr_scene_*.json 또는 scene.json)이 없다: {EPISODE}")
SCENE = json.load(open(_scene_files[0], encoding="utf-8"))
META = _meta(EPISODE)
_ph = os.path.join(EPISODE, "phases.json")
PHASES = json.load(open(_ph, encoding="utf-8"))["phases"] if os.path.isfile(_ph) else []
_init = os.path.join(EPISODE, "initial_state.json")
INIT = json.load(open(_init, encoding="utf-8")) if os.path.isfile(_init) else None

PRODUCTS = [{"slug": p["slug"], "pos": tuple(float(v) for v in p["pos"]),
             "quat": tuple(float(v) for v in p["quat"])} for p in SCENE["products"]]
for p in PRODUCTS:
    if p["slug"] not in P.PRODUCTS:
        raise SystemExit(f"장면의 상품이 8 종에 없다: {p['slug']}")
N = len(ACTIONS) if args_cli.frames <= 0 else min(args_cli.frames, len(ACTIONS))
REC_HZ = 30.0 if TS is None or len(TS) < 2 else 1.0 / float(np.median(np.diff(TS)))
order = META.get("chain_order") or [PRODUCTS[0]["slug"]]
print(f"\n[재생] {os.path.basename(EPISODE)}  상품 {' -> '.join(order)}  "
      f"{N} 프레임 ({N / REC_HZ:.1f} 초 @ {REC_HZ:.0f} Hz)  물리 {args_cli.substeps} 걸음/프레임", flush=True)
for ph in PHASES:
    if ph.get("name"):
        pass
print(f"[재생] 장면 {os.path.basename(_scene_files[0])}: " + ", ".join(
    f"{k}:{p['slug']}" for k, p in enumerate(PRODUCTS)), flush=True)

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch                                                          # noqa: E402
import omni.usd                                                       # noqa: E402
import isaaclab.sim as sim_utils                                      # noqa: E402
from isaaclab.assets import AssetBaseCfg, RigidObjectCfg              # noqa: E402
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg      # noqa: E402
from isaaclab.sensors import CameraCfg                                # noqa: E402
from isaaclab.utils import configclass                                # noqa: E402

from cyclo_lab.assets.robots.FFW_SG2 import (                         # noqa: E402
    FFW_SG2_MOBILE_CFG, SG2_SWERVE_STEERING_JOINTS, SG2_SWERVE_WHEEL_JOINTS,
)


def _by_path(name, path):
    spec = _ilu.spec_from_file_location(name, path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_TASKA = os.path.join(_HERE, "taskA")
taskA_colliders = _by_path("taskA_colliders", f"{_TASKA}/taskA_colliders.py")
robot_pose = _by_path("taskA_robot_pose", f"{_TASKA}/taskA_robot_pose.py")
from taskC import taskC_counter as counter                            # noqa: E402


def _cam(name):
    c = L.CAMERAS[name]
    return CameraCfg(
        prim_path="{ENV_REGEX_NS}/Robot/" + c["rel"],
        update_period=1.0e9, height=c["h"], width=c["w"], data_types=["rgb"],
        update_latest_camera_pose=True,
        spawn=sim_utils.PinholeCameraCfg(focal_length=c["focal"], focus_distance=c["focus"],
                                         horizontal_aperture=c["aperture"],
                                         clipping_range=c["clip"]),
        offset=CameraCfg.OffsetCfg(pos=c["offset_pos"], rot=c["offset_rot"], convention="isaac"))


@configclass
class World(InteractiveSceneCfg):
    """task_c_demo.py 와 같은 장면. 상품은 기록의 장면 JSON 그대로."""

    store = AssetBaseCfg(
        prim_path="{ENV_REGEX_NS}/Store",
        spawn=sim_utils.UsdFileCfg(usd_path=STORE_USD),
        init_state=AssetBaseCfg.InitialStateCfg(pos=(0.0, 0.0, 0.0)))
    ground = AssetBaseCfg(
        prim_path="/World/GroundPlane",
        spawn=sim_utils.GroundPlaneCfg(),
        init_state=AssetBaseCfg.InitialStateCfg(pos=(0.0, 0.0, 0.0)))
    robot = FFW_SG2_MOBILE_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
    head_cam = _cam("head_cam")
    left_wrist_cam = _cam("left_wrist_cam")
    right_wrist_cam = _cam("right_wrist_cam")

    def __post_init__(self):
        spos = L.robot_to_world(L.SCANNER_HOLD_POS)
        self.scanner = RigidObjectCfg(
            prim_path="{ENV_REGEX_NS}/Scanner",
            spawn=sim_utils.UsdFileCfg(
                usd_path=SCANNER_USD,
                rigid_props=sim_utils.RigidBodyPropertiesCfg(
                    disable_gravity=True, linear_damping=5.0, angular_damping=5.0)),
            init_state=RigidObjectCfg.InitialStateCfg(
                pos=tuple(float(v) for v in spos),
                rot=tuple(float(v) for v in L.quat_robot_to_world(L.SCANNER_HOLD_QUAT))))
        for k, d in enumerate(PRODUCTS):
            setattr(self, f"p_{k}", RigidObjectCfg(
                prim_path=f"{{ENV_REGEX_NS}}/P_{k}",
                spawn=sim_utils.UsdFileCfg(
                    usd_path=str(P.product_usd(d["slug"])),
                    rigid_props=sim_utils.RigidBodyPropertiesCfg(
                        disable_gravity=False, linear_damping=1.0, angular_damping=2.0)),
                init_state=RigidObjectCfg.InitialStateCfg(
                    pos=tuple(float(v) for v in L.robot_to_world(d["pos"])),
                    rot=tuple(float(v) for v in L.quat_robot_to_world(d["quat"])))))


def main():
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=PHYSICS_DT, device=args_cli.device))
    scene = InteractiveScene(World(num_envs=1, env_spacing=8.0))
    stage = omni.usd.get_context().get_stage()
    taskA_colliders.harden(stage, log=lambda *a: None)
    _log = lambda m: print(f"[i] {m}", flush=True)  # noqa: E731
    counter.deactivate_duplicates(stage, log=_log)
    counter.remove_low_shelf(stage, log=_log)
    sim.reset()
    counter.draw_band(log=_log)

    robot = scene["robot"]
    names = list(robot.joint_names)
    rec_ids, _ = robot.find_joints(REC_JOINTS, preserve_order=True)
    slave_l, _ = robot.find_joints([f"gripper_l_joint{i}" for i in (2, 3, 4)], preserve_order=True)
    slave_r, _ = robot.find_joints([f"gripper_r_joint{i}" for i in (2, 3, 4)], preserve_order=True)
    steer_ids, _ = robot.find_joints(list(SG2_SWERVE_STEERING_JOINTS), preserve_order=True)
    wheel_ids, _ = robot.find_joints(list(SG2_SWERVE_WHEEL_JOINTS), preserve_order=True)
    wheel_bodies = [i for i, n in enumerate(robot.body_names) if "wheel_drive_link" in n]
    dev = sim.device
    zero_steer = torch.zeros((1, len(steer_ids)), device=dev)
    zero_wheel = torch.zeros((1, len(wheel_ids)), device=dev)
    render = not args_cli.headless
    step_count = [0]
    IL, IR = REC_JOINTS.index("gripper_l_joint1"), REC_JOINTS.index("gripper_r_joint1")

    def command(q19):
        """22 열 기록 한 줄을 로봇 목표로. 그리퍼 종속 관절(2~4)은 마스터와 같은 값을 준다."""
        t = torch.as_tensor(np.asarray(q19[:len(REC_JOINTS)], dtype=np.float32), device=dev).unsqueeze(0)
        robot.set_joint_position_target(t, joint_ids=rec_ids)
        robot.set_joint_position_target(t[:, IL:IL + 1].repeat(1, 3), joint_ids=slave_l)
        robot.set_joint_position_target(t[:, IR:IR + 1].repeat(1, 3), joint_ids=slave_r)
        robot.set_joint_position_target(zero_steer, joint_ids=steer_ids)
        robot.set_joint_velocity_target(zero_wheel, joint_ids=wheel_ids)

    def step(q19, do_render=True):
        command(q19)
        scene.write_data_to_sim()
        sim.step(render=do_render and render and step_count[0] % RENDER_EVERY == 0)
        scene.update(PHYSICS_DT)
        step_count[0] += 1

    q0 = (np.array([INIT["robot_joint_pose"][n] for n in REC_JOINTS], dtype=np.float64)
          if INIT and all(n in INIT.get("robot_joint_pose", {}) for n in REC_JOINTS) else JOINTS[0][:len(REC_JOINTS)])

    # ---- 로봇을 계산대 앞에 세운다 (데모와 같은 방식). 관절은 기록의 첫 프레임 자세로.
    scene.update(PHYSICS_DT)
    origin = scene.env_origins[0]
    spawn_quat, spawn_z = robot_pose.spawn_pose(robot, origin)
    want = robot.data.default_joint_pos[0].clone()
    for n, v in zip(REC_JOINTS, q0):
        want[names.index(n)] = float(v)
    for n in [f"gripper_l_joint{i}" for i in (2, 3, 4)]:
        want[names.index(n)] = float(q0[IL])
    for n in [f"gripper_r_joint{i}" for i in (2, 3, 4)]:
        want[names.index(n)] = float(q0[IR])
    robot.write_joint_state_to_sim(want.unsqueeze(0), torch.zeros_like(want).unsqueeze(0))
    scene.write_data_to_sim()
    rx, ry = L.ROBOT_BASE_WORLD[0], L.ROBOT_BASE_WORLD[1]
    z = spawn_z
    for _ in range(2):
        robot_pose.place(robot, origin, (rx, ry), L.ROBOT_YAW, spawn_quat, z)
        scene.write_data_to_sim()
        step(q0, do_render=False)
        low = min(float(robot.data.body_pos_w[0, i][2]) for i in wheel_bodies)
        z -= low - WHEEL_RADIUS
    robot_pose.place(robot, origin, (rx, ry), L.ROBOT_YAW, spawn_quat, z)
    scene.write_data_to_sim()

    def _set_root(obj, pos_w, quat_w):
        st = obj.data.root_state_w[0].clone()
        st[:3] = torch.as_tensor(np.asarray(pos_w, dtype=np.float32), device=st.device) \
            + torch.as_tensor(np.asarray(origin.cpu(), dtype=np.float32), device=st.device)
        st[3:7] = torch.as_tensor(np.asarray(quat_w, dtype=np.float32), device=st.device)
        st[7:] = 0.0
        obj.write_root_state_to_sim(st.unsqueeze(0))

    for k, d in enumerate(PRODUCTS):
        _set_root(scene[f"p_{k}"], L.robot_to_world(d["pos"]), L.quat_robot_to_world(d["quat"]))
    _set_root(scene["scanner"], L.robot_to_world(L.SCANNER_HOLD_POS), L.quat_robot_to_world(L.SCANNER_HOLD_QUAT))
    scene.write_data_to_sim()
    for _ in range(int(args_cli.start_hold / PHYSICS_DT)):
        step(q0)

    def prod_pos_r(k):
        pw = (scene[f"p_{k}"].data.root_pos_w[0] - origin).cpu().numpy()
        return L.world_to_robot(tuple(float(v) for v in pw))

    start_pos = [prod_pos_r(k) for k in range(len(PRODUCTS))]
    scan_r = np.asarray(L.SCANNER_HOLD_POS, dtype=float)
    stat = [{"slug": d["slug"], "max_lift_mm": 0.0, "min_scanner_mm": 1e9, "min_scanner_frame": -1,
             "moved_mm": 0.0} for d in PRODUCTS]
    ph_at = {int(p["start_frame"]): p["name"] for p in PHASES if p.get("name")}
    x0, x1, y0, y1 = L.band_inner()
    t_wall = None
    import time as _time
    t_wall = _time.time()
    print(f"[재생] 시작 -- 첫 프레임 자세로 {args_cli.start_hold:.1f} 초 세운 뒤 튼다\n", flush=True)
    for k in range(N):
        if k in ph_at:
            print(f"[재생] {k / REC_HZ:6.1f}초  국면 {ph_at[k]}", flush=True)
        a = ACTIONS[k]
        b = ACTIONS[min(k + 1, N - 1)]
        for s in range(max(1, args_cli.substeps)):
            q = a if args_cli.no_interp else a + (b - a) * (s / float(max(1, args_cli.substeps)))
            step(q)
        for i in range(len(PRODUCTS)):
            pr = prod_pos_r(i)
            lift = (pr[2] - start_pos[i][2]) * 1000.0
            dsc = float(np.linalg.norm(np.asarray(pr) - scan_r)) * 1000.0
            st = stat[i]
            st["max_lift_mm"] = max(st["max_lift_mm"], lift)
            if dsc < st["min_scanner_mm"]:
                st["min_scanner_mm"], st["min_scanner_frame"] = dsc, k
            st["moved_mm"] = max(st["moved_mm"], float(np.hypot(pr[0] - start_pos[i][0], pr[1] - start_pos[i][1])) * 1000.0)
        if k % int(REC_HZ * 10) == 0 and k > 0:
            el = _time.time() - t_wall
            print(f"[재생] {k / REC_HZ:6.1f}초 / {N / REC_HZ:.1f}초  (실시간 대비 x{(k / REC_HZ) / max(el, 1e-6):.2f})", flush=True)

    print("\n[재생] 끝. 상품별 결과 (로봇 좌표, 기록의 첫 프레임 기준)", flush=True)
    result = {"episode": os.path.basename(EPISODE), "frames": int(N), "hz": REC_HZ, "products": []}
    for i, d in enumerate(PRODUCTS):
        pr = prod_pos_r(i)
        inside = (x0 <= pr[0] <= x1) and (y0 <= pr[1] <= y1)
        dz_end = (pr[2] - start_pos[i][2]) * 1000.0
        st = stat[i]
        verdict = ("들어올림 O" if st["max_lift_mm"] > 20.0 else "들어올림 X")
        print(f"  {i}: {d['slug']:<26s} 최대 들림 {st['max_lift_mm']:6.1f} mm  스캐너 최근접 {st['min_scanner_mm']:6.1f} mm "
              f"(f{st['min_scanner_frame']})  최종 자리 ({pr[0]:+.3f}, {pr[1]:+.3f}, {pr[2]:.3f}) "
              f"{'띠 안' if inside else '띠 밖'}  최종 높이차 {dz_end:+.1f} mm  {verdict}", flush=True)
        result["products"].append({"slot": i, "slug": d["slug"], "max_lift_mm": round(st["max_lift_mm"], 1),
                                   "min_scanner_mm": round(st["min_scanner_mm"], 1),
                                   "min_scanner_frame": st["min_scanner_frame"],
                                   "final_pos_robot": [round(float(v), 4) for v in pr],
                                   "inside_band": bool(inside), "moved_mm": round(st["moved_mm"], 1)})
    if args_cli.summary_json:
        with open(args_cli.summary_json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1)
        print(f"[재생] 요약을 {args_cli.summary_json} 에 적었다", flush=True)


main()
_exit_guard = _threading.Timer(10.0, os._exit, (0,))
_exit_guard.daemon = True
_exit_guard.start()
simulation_app.close()
