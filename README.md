# Humanoid Challenge — 참가자 환경

ROBOTIS **AI Worker (FFW-SG2)** 휴머노이드로 편의점 업무를 수행하는 시뮬레이션 대회의
**참가자용 환경 저장소**입니다. 이 저장소로 대회와 동일한 시뮬레이션 환경(Isaac Sim 5.1 /
Isaac Lab 2.3 기반)을 로컬에서 띄워 데이터를 수집하고 방법론을 개발할 수 있습니다.

> **평가는 주최 측 서버에서 진행됩니다.** 여러분은 정책(추론) 서버를 띄우고 홈페이지에서
> 주소를 제출하면, 평가 서버가 closed-loop으로 관측을 보내고 액션을 받아 채점합니다.
> 이 저장소는 평가를 실행하지 않습니다 — 개발·사전 점검용 로컬 환경입니다.

| 과제 | 한 줄 요약 | 로봇 상태 |
|---|---|---|
| **A. 진열대로 이동** | 임의 지점에서 출발해 장애물을 피해 목표 진열대 앞까지 | 주행 |
| **B. 상품 진열** | 바구니의 상품을 집어 진열대의 지정 위치에 배치 | 정지 |
| **C. 인식 및 연산** | 계산대의 상품을 집으며 품목 인식·총액 계산 | 정지 |

## 저장소 구성

```
docker/       # 도커 실행 구성 — 이미지 안에 환경·에셋이 들어 있습니다
scripts/      # 데모 스크립트 — 컨테이너의 /workspace/challenge_scripts 로 마운트됩니다
workspace/    # 여러분의 작업 공간 — 컨테이너의 /workspace/user 로 마운트 (git 미추적)
```

- 환경 코드·로봇·편의점 에셋은 배포 이미지에 포함되어 있습니다. 그 이미지를 무엇으로
  어떻게 만드는지는 `docker/Dockerfile` 과 `docker/build_image.sh` 에 그대로 적혀
  있습니다 — 참가자가 쓸 일은 없지만, 이미지에 무엇이 들어 있고 무엇을 뺐는지는
  그 두 파일이 정본입니다.
- `scripts/`는 마운트라서, 스크립트가 늘어나면 `git pull` 만으로 컨테이너를 다시
  만들지 않고 바로 쓸 수 있습니다. 지금 들어 있는 것은 아래 **과제 B 장면 둘러보기**의
  `task_b_demo.py` 하나입니다.
- **추가 예정 — 평가 사전 점검 스크립트**: 평가가 어떤 식으로 진행되는지(관측 →
  정책 서버 → 액션 → 시뮬 스텝) 제출 전에 로컬에서 확인할 수 있는 스크립트를
  준비 중입니다.

## 요구사항

- Ubuntu 22.04 (x86-64), NVIDIA GPU — **VRAM 8GB 이상, 12GB 이상 권장**
  (렌더 포함 시뮬 프로세스 1개가 4~6GB를 사용합니다)
- NVIDIA 드라이버: [Isaac Sim 5.1 요구사항](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html) 충족 버전
- Docker + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- GUI 사용 시: X11 세션 (Wayland는 XWayland 경유)

## 시작하기

```bash
git clone git@github.com:kairobahq/humanoid-challenge-env.git
cd humanoid-challenge-env/docker

# 1) Isaac Sim EULA 동의 — .env 에서 ACCEPT_EULA=Y 로 직접 설정하세요.
#    (NVIDIA Omniverse EULA 에 본인이 동의하는 것입니다)
vi .env

# 2) 이미지 받기 + 컨테이너 기동 (headless)
docker compose pull
docker compose up -d

# 3) 컨테이너 진입
docker exec -it challenge_env bash
```

> 배포 이미지 주소는 `.env` 의 `CHALLENGE_IMAGE` 입니다. **대회 공지에서 확정 주소를
> 확인**하고 값이 다르면 갱신하세요.

### 컨테이너 안에서 스크립트 실행하기 — 규약 3가지

```bash
# 컨테이너 안 (또는 docker exec ... bash -lc '...')
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u <스크립트.py> --headless --enable_cameras
```

1. **인터프리터는 경로로 부르세요.** `python` alias 는 대화형 셸에서만 풀리므로
   `docker exec` 로 실행하면 `python: command not found` 가 납니다.
2. **`-u` 를 붙이세요.** Isaac 은 종료 시 프로세스를 그대로 뜯어내서, 버퍼링된
   출력이 통째로 사라집니다 — 출력이 없는 것처럼 보이면 대부분 이것입니다.
3. **카메라를 쓰는 태스크는 `--enable_cameras` 가 필수**입니다 (없으면
   `RuntimeError: A camera was spawned without the --enable_cameras flag`).

기동에는 **30~60초**가 걸리고 그동안 경고 로그가 대량으로 출력됩니다 — 정상입니다.
등록된 태스크 목록은 `scripts/tools/list_envs.py` 로 확인할 수 있습니다.

## 과제 B 장면 둘러보기

환경이 실제로 어떻게 생겼는지 보는 가장 빠른 길입니다. **과제 B 의 에피소드가 시작되는
순간**을 만들어 세워 두고 거기서 멈춥니다 — 집지도, 놓지도, 움직이지도 않습니다.
보여 주려는 것이 여러분의 정책이 첫 관측으로 받게 될 바로 그 그림이기 때문입니다.

```bash
# 컨테이너 안에서 (GUI 로 띄웠다면 창이 뜹니다)
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000
```

장면에 있는 것:

* **진열대** — 다섯 단이 상품으로 차 있고, 위 두 단(3단·2단)의 앞줄에서 1~3 칸이
  비어 있습니다. 비어 있는 칸 **뒤에는 그 칸에 들어가야 할 상품이 서 있습니다** —
  무엇을 채워야 하는지는 진열대를 보면 읽을 수 있습니다.
* **책상 위 파란 상자** — 빈 칸 수만큼 상품이 들어 있습니다. 상자의 *i* 번째 상품이
  *i* 번째 빈 칸에 들어갑니다.
* **로봇** — 진열대를 마주 보고, **바퀴가 바닥에 닿은 채로** 섭니다. 공중에서
  떨어지지 않습니다.

한 장면은 `--seed` 하나가 전부 정합니다. 같은 값이면 어디서 몇 번을 돌려도 같은
장면입니다. 장면 내용을 글과 JSON 으로 받는 법을 포함한 나머지는
**[`scripts/README.md`](scripts/README.md)** 에 있습니다.

> 과제 A 와 C 의 장면도 같은 방식으로 하나씩 추가됩니다.

## GUI 로 띄우기

시뮬레이션을 화면으로 보려면 X11 오버레이를 겹쳐 기동합니다:

```bash
# 호스트에서 — X 서버 접근 허용 (로컬 컨테이너만, 세션당 1회)
xhost +local:root

cd docker
docker compose -f docker-compose.yaml -f x11.yaml up -d
docker exec -it challenge_env bash
```

컨테이너 안에서 `--headless` 를 **빼고** 실행하면 Isaac Sim 창이 뜹니다:

```bash
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u <스크립트.py> --enable_cameras   # GUI
```

GUI 가 안 뜰 때: ① `echo $DISPLAY` 가 컨테이너 안에서 비어 있지 않은지,
② 호스트에서 `xhost +local:root` 를 했는지, ③ Wayland 세션이면 XWayland 가
동작 중인지 순서로 확인하세요.

## 정책 서버와 제출

정책 서버 템플릿(WebSocket + msgpack 프로토콜, 예시 정책 포함)과 제출 방법은
**대회 홈페이지**에서 안내합니다. 컨테이너는 `network_mode: host` 라서, 호스트에서
띄운 정책 서버가 컨테이너 안에서도 `127.0.0.1` 로 그대로 보입니다 — 데모 스크립트가
제공되면 이 구조로 로컬 사전 점검을 하게 됩니다.

## 평가 사전 점검 스크립트 (추가 예정)

위 `task_b_demo.py` 는 장면을 보여 줄 뿐 정책을 부르지 않습니다. 평가 프리셋을 정책
서버와 함께 미리 돌려 볼 수 있는 스크립트를 준비 중입니다. 예정 흐름:

1. 여러분의 정책 서버를 호스트에서 기동
2. `scripts/` 의 데모 스크립트가 컨테이너 안에서 환경을 띄우고, 평가 서버와 동일한
   방식으로 관측을 보내고 액션 청크를 받아 시뮬레이션을 진행
3. 종료 후 에피소드 요약 출력

구체 인터페이스는 확정 후 이 절과 `scripts/README.md` 를 갱신해 공지합니다.

## 라이선스 고지

배포 이미지에 함께 묶이는 구성요소와 각 라이선스입니다. 대회 측이 별도로 수정한
구성요소는 없으며(로봇 USD 원본 무수정 사용), 라이선스 전문은 이미지 안
`/workspace/cyclo_lab` 의 `LICENSE` / `LICENSE-IsaacLab` / `THIRD_PARTY_LICENSES.md`
에 포함되어 있습니다.

| 구성요소 | 라이선스 | 비고 |
|---|---|---|
| Isaac Sim (베이스 이미지) | [NVIDIA Omniverse EULA](https://docs.omniverse.nvidia.com/platform/latest/common/NVIDIA_Omniverse_License_Agreement.html) | `.env` 의 `ACCEPT_EULA=Y` 설정 = 본인 동의 |
| Isaac Lab | BSD-3-Clause | 원본 무수정 포함 |
| 대회 환경 코드 (cyclo_lab) | Apache-2.0 | |
| ROBOTIS 로봇 모델 (FFW-SG2, [robotis_lab](https://github.com/ROBOTIS-GIT/robotis_lab)) | Apache-2.0 | 원본 USD 무수정 사용 |
| Eclipse Cyclone DDS | EPL-2.0 / EDL-1.0 | |
| whole_body_tracking 차용 코드 | MIT | 환경 저장소 `THIRD_PARTY_LICENSES.md` 고지 |
| 편의점 상품·집기 에셋 | 주최 측 제공 | 대회 참가 목적 사용 (별도 고지 시 갱신) |

## 문의

대회 홈페이지의 QnA 게시판을 이용해 주세요.
