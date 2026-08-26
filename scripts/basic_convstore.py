"""편의점 매장 기본 씬 — 씬을 불러와 로봇을 세워 두고 멈춘다.

    ${ISAACLAB_PATH}/_isaac_sim/python.sh -u /workspace/challenge_scripts/basic_convstore.py

조작은 없다. 매장 전체(진열대·냉장고·계산대·통로)와 로봇이 서 있는 그림을 보여 주는
것이 전부다. 로봇을 움직이는 것은 여러분의 코드 몫이다.
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="편의점 매장 기본 씬을 띄운다.")
parser.add_argument("--task", default="Cyclo-PickPlace-FFW-SG2-ConvStore-Drive-v0",
                    help="씬을 정하는 태스크 id")
parser.add_argument("--seconds", type=float, default=0.0,
                    help="몇 초 동안 유지할지. 0 이면 창을 닫을 때까지")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
args.enable_cameras = True            # 로봇이 카메라를 달고 있어 이 깃발 없이는 스폰이 막힌다

app = AppLauncher(args).app

import gymnasium as gym                                               # noqa: E402
import torch                                                          # noqa: E402
from isaaclab_tasks.utils import parse_env_cfg                        # noqa: E402

import cyclo_lab.simulation_tasks  # noqa: E402,F401  -- Cyclo-* 태스크 등록

cfg = parse_env_cfg(args.task, num_envs=1)
cfg.episode_length_s = 1.0e9          # 구경하는 동안 에피소드가 끝나 씬이 리셋되지 않게
env = gym.make(args.task, cfg=cfg)
env.reset()
zero = torch.zeros((1, env.action_space.shape[-1]), device=env.unwrapped.device)

print("[basic_convstore] 매장 씬 준비 끝. 창을 닫으면 종료합니다.", flush=True)
ticks = 0
while app.is_running():
    env.step(zero)                    # 0 액션 = 제자리
    ticks += 1
    if args.seconds and ticks * env.unwrapped.step_dt >= args.seconds:
        break

env.close()
app.close()
