# 배포용 정본 -- 대회 환경 저장소 `Task-A/sim/robot_pose.py` 에서 그대로 옮겼다. 한 줄도
# 고치지 않았다.
#
# 이 파일이 없으면 안 되는 이유: 좌석 12 곳은 yaw 가 저마다 다르고, yaw 쿼터니언을 새로
# 만들어 씌우면 **로봇이 옆으로 눕는다.** 아래 원본 기록이 그 대가를 적고 있다.
# ---------------------------------------------------------------------------------------------

# Copyright 2025.
#
# Put the robot somewhere without knocking it over.
#
# THE BUG THIS EXISTS TO PREVENT
#   Every script here placed the robot with
#
#       quat = quat_from_euler_xyz(0, 0, yaw)
#       robot.write_root_pose_to_sim(cat([pos, quat]))
#
#   which reads as "face this way, upright". It is not. It says roll = 0 and pitch = 0 IN THE
#   ROOT LINK'S OWN FRAME, and FFW-SG2's root link is not upright at identity -- measured
#   2026-08-13, a standing robot's root quaternion is [0.3800, 0.3802, -0.5964, -0.5961]. Writing
#   a pure yaw over that lays the robot flat: its own +Z came out at (-0.907, 0.422, -0.001) in
#   the world, exactly 90.0 degrees from vertical, with the root 0.30 m off the floor instead of
#   1.43.
#
#   It cost the whole of the pick work. The arms were driven, the IK rewritten, the Jacobian
#   columns corrected and the frames converted, all against a robot lying on its side -- which is
#   why the crate read as 1.80 m "below" the root, why the hands went backwards, and why an arm
#   that reaches 0.79 m reached it into empty air. None of those were the bug; all of them were
#   the same bug seen from different angles.
#
# THE RULE
#   Never build the root orientation from scratch. Read the one the robot spawns with, and turn
#   THAT about the world's vertical.

import math

import torch

import isaaclab.utils.math as math_utils


def spawn_pose(robot, env_origin):
    """The orientation and height the robot has at reset, to be reused for every later placement.

    Call once, after sim.reset() and scene.update(), before anything moves the robot.
    """
    return robot.data.root_quat_w[0].clone(), (robot.data.root_pos_w[0, 2] - env_origin[2]).item()


def quat_for_yaw(spawn_quat, yaw: float):
    """`spawn_quat` turned by `yaw` about the WORLD's vertical.

    Pre-multiplied, so the turn happens in the world and not about whatever axis the root link
    happens to call up.
    """
    device = spawn_quat.device
    qz = math_utils.quat_from_euler_xyz(
        torch.zeros(1, device=device), torch.zeros(1, device=device),
        torch.tensor([float(yaw)], device=device))
    return math_utils.quat_mul(qz, spawn_quat.unsqueeze(0))


def place(robot, env_origin, xy, yaw: float, spawn_quat, z: float):
    """Stand the robot at `xy` facing `yaw`, keeping the orientation it was built with."""
    device = robot.device
    pos = torch.tensor([[float(xy[0]), float(xy[1]), float(z)]], device=device) + env_origin
    quat = quat_for_yaw(spawn_quat, yaw)
    ids = torch.arange(1, device=device)
    robot.write_root_pose_to_sim(torch.cat([pos, quat], dim=-1), env_ids=ids)
    robot.write_root_velocity_to_sim(torch.zeros(1, 6, device=device), env_ids=ids)


def tilt_degrees(robot):
    """How far the robot's own up-axis is from the world's vertical. 0 is standing, 90 is flat."""
    device = robot.device
    up = math_utils.quat_apply(robot.data.root_quat_w[0].unsqueeze(0),
                               torch.tensor([[0.0, 0.0, 1.0]], device=device))[0]
    return math.degrees(math.acos(max(-1.0, min(1.0, up[2].item())))), up


def assert_upright(robot, log=print, limit: float = 15.0) -> bool:
    """Report the tilt and say plainly whether the robot is standing.

    Called after every placement in the scripts here. A measurement taken from a robot on its side
    is not a wrong number, it is an answer to a different question, and the only way to tell is to
    ask.
    """
    tilt, up = tilt_degrees(robot)
    ok = tilt < limit
    log(f"기울기 {tilt:.1f}도, 위쪽 축 ({up[0]:.3f}, {up[1]:.3f}, {up[2]:.3f}) "
        f"-> {'서 있음' if ok else '누워 있음 -- 이 상태의 측정은 무효다'}")
    return ok
