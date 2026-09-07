"""편의점 매장 기본 씬 — 씬을 불러와 로봇을 세워 두고 멈춘다.

    ${ISAACLAB_PATH}/_isaac_sim/python.sh -u /workspace/challenge_scripts/basic_convstore.py

조작은 없다. 매장 전체(진열대·냉장고·계산대·통로)와 로봇이 서 있는 그림을 보여 주는
것이 전부다. 로봇을 움직이는 것은 여러분의 코드 몫이다.

씬은 과제 A 의 시작 장면(`task_a_demo.py`)을 그대로 쓴다 -- 배포 이미지에 들어 있는
매장 USD 와 로봇으로 서는 장면이 그것이다. 옵션은 `task_a_demo.py` 와 같다
(`--seed`, `--seconds`, `--headless`, `--shot FILE.png` ...). seed 를 주지 않으면 1000.
"""

import os
import sys

_DEMO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "task_a_demo.py")
_argv = sys.argv[1:]
if "--seed" not in _argv:
    _argv = ["--seed", "1000"] + _argv
os.execv(sys.executable, [sys.executable, "-u", _DEMO] + _argv)
