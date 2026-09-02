# Humanoid Challenge — 참가자 환경

ROBOTIS **AI Worker (FFW-SG2)** 휴머노이드로 편의점 일을 시키는 시뮬레이션 대회입니다.
이 저장소로 대회와 똑같은 환경(Isaac Sim 5.1 / Isaac Lab 2.3)을 각자 컴퓨터에 띄워
데이터를 모으고 방법을 만들 수 있습니다.

> **채점은 주최 측 서버에서 합니다.** 참가자는 정책 서버를 띄우고 홈페이지에 주소를
> 내면, 채점 서버가 관측을 보내고 동작을 받아 점수를 매깁니다. 이 저장소는 채점을
> 하지 않습니다. 개발하고 미리 확인해 보는 용도입니다.

## 세 과제

| | 과제 | 하는 일 | 로봇 |
|---|---|---|---|
| **A** | 진열대로 이동 | 시식 탁상에서 바구니를 집어, 장애물을 피해 목적지 진열대 옆 책상에 옮겨 놓는다 | 주행 |
| **B** | 상품 진열 | 가져온 상자에서 상품을 꺼내 진열대의 빈 칸에 놓는다 | 정지 |
| **C** | 인식과 계산 | 계산대의 상품을 하나씩 집으면서 무엇인지 알아보고 값을 더한다 | 정지 |

지금 이 저장소에는 **과제 A 와 과제 B 의 장면**이 들어 있습니다. C 도 같은 방식으로
추가됩니다.

## 저장소 구성

```
docker/       도커 실행 구성. 환경 코드(cyclo_lab)와 에셋은 배포 이미지 안에 들어 있습니다
scripts/      주최측 제공 스크립트 — 씬 생성기(task 별)와 데모 평가 서버.
              컨테이너의 /workspace/challenge_scripts 로 붙습니다
  taskA/          과제 A 의 장면 정의 — 12 좌석, 목적지, 스툴, 실측값. 읽어 보셔도 됩니다
  demos/          과제 B 시연 기록 일곱 판. task_b_replay.py 가 읽습니다
  demo_server/    채점과 같은 방식으로 정책 서버를 붙여 보는 데모 평가 서버 (준비 중)
run/          실행 진입점. run_gui.sh 가 GUI 로 컨테이너를 띄우고,
              run_task_*.bash 가 해당 과제의 씬을 랜덤하게 하나 생성해 띄웁니다 (준비 중)
workspace/    참가자 작업 공간. 컨테이너의 /workspace/user 로 붙습니다 (git 미추적)
```

`scripts/` 와 `workspace/` 는 마운트라서, 내용이 늘어나면 `git pull` 만 하면
컨테이너를 다시 만들지 않고 바로 쓸 수 있습니다.

이미지를 무엇으로 어떻게 굽는지는 `docker/Dockerfile` 과 `docker/build_image.sh` 에
그대로 적혀 있습니다. 참가자가 쓸 일은 없지만, 이미지에 무엇이 들어갔고 무엇을
뺐는지는 그 두 파일이 정본입니다.

## 요구사항

- Ubuntu 22.04 (x86-64), NVIDIA GPU — **VRAM 8 GB 이상, 12 GB 이상 권장**
  (진열대 하나를 세우는 과제 B 가 4~6 GB, 편의점 전체가 뜨는 **과제 A 는 6.5 GB** 를
  씁니다 — 2026-08-26 실측. 8 GB 로도 뜨지만 여유가 얼마 없습니다)
- NVIDIA 드라이버: [Isaac Sim 5.1 요구사항](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html)을 채우는 버전
- Docker 와 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- 화면으로 보려면 X11 세션 (Wayland 는 XWayland 를 거칩니다)

## 시작하기

```bash
git clone git@github.com:kairobahq/humanoid-challenge-env.git
cd humanoid-challenge-env

# 1) Isaac Sim 사용 조건에 동의합니다 — docker/.env 에서 ACCEPT_EULA=Y 로 바꾸세요.
#    (NVIDIA Isaac Sim 라이선스에 본인이 동의한다는 뜻입니다)
vi docker/.env

# 2) 이미지를 여러분 머신에서 만듭니다 (처음 20~40 분) — 이 한 줄이 Isaac Sim 바탕
#    이미지 받기 + 대회 환경 설치까지 전부 합니다
./run/setup.sh

# 3) 컨테이너를 띄우고 들어갑니다 (화면 없이)
cd docker
docker compose up -d
docker exec -it challenge_env bash
```

> `container ... is not running` 이 나오면 `docker logs challenge_env` 를 보세요.
> 대부분 1번(ACCEPT_EULA)을 건너뛴 경우입니다.

> **이미지를 미리 구워 나눠 주지 않는 이유** — Isaac Sim 컨테이너의 라이선스(NVIDIA
> Isaac Sim Additional Software and Materials License)가 제3자 재배포를 허용하지
> 않습니다. 그래서 NVIDIA 바탕 이미지는 각자 NVIDIA 레지스트리에서 직접 받고(1번의
> 동의가 그 조건입니다), 대회 쪽 코드와 에셋만 오버레이 아카이브로 배포합니다.

### 스크립트를 돌리는 세 가지 규칙

```bash
# 컨테이너 안에서 (또는 docker exec ... bash -lc '...')
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u <스크립트.py> --headless --enable_cameras
```

1. **파이썬은 경로로 부르세요.** `python` 별칭은 대화형 셸에서만 풀립니다.
   `docker exec` 로 돌리면 `python: command not found` 가 납니다.
2. **`-u` 를 붙이세요.** Isaac 은 끝날 때 프로세스를 그대로 뜯어내서, 모아 둔 출력이
   통째로 사라집니다. 아무것도 안 찍힌 것처럼 보이면 대개 이것 때문입니다.
3. **카메라를 쓰는 과제는 `--enable_cameras` 가 꼭 있어야 합니다.** 없으면
   `RuntimeError: A camera was spawned without the --enable_cameras flag` 가 납니다.

뜨는 데 **30~60 초**가 걸리고 그동안 경고가 잔뜩 나옵니다. 정상입니다.

## 과제 A 둘러보기

환경이 어떻게 생겼는지 보는 가장 빠른 길입니다. **에피소드가 시작되는 순간**을 만들어
세워 놓고 거기서 멈춥니다. 집지도, 몰지도, 놓지도 않습니다. 여러분의 정책이 첫 관측으로
받게 될 그림을 그대로 보여 주는 것이 목적입니다.

```bash
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_a_demo.py --seed 1000
```

<br>

**매장** — 편의점 전체가 들어옵니다. 통로 세 줄, 곤돌라, 냉장고, 냉동고, 와인 진열대,
계산대, 그리고 시식 코너. 과제 B 와 C 가 진열대 하나 앞에서 벌어지는 것과 달리 과제 A 는
매장을 가로지릅니다. **통로는 Y 방향입니다.**

**시식 탁상과 좌석** — 원형 탁상 3 개를 4 등분한 **12 개 고정 좌석** 중 하나에서
시작합니다. 매장 어디서나 임의로 출발하던 예전 정의는 폐기됐습니다. 로봇은 탁상을 마주
보고 서고, 그 탁상 위에 파란 바구니가 놓여 있습니다.

**바구니** — 탁상 위 파란 상자(0.380 × 0.590 × 0.140 m). 이것을 집어서 가져가야 합니다.
긴 면이 로봇을 향하도록 놓입니다.

**목적지와 책상** — 목표 진열대 앞의 도착 자리, 그리고 그 옆 책상. 바구니는 그 책상 위에
놓여야 합니다. 좌석에 따라 직선으로 9.3 ~ 11.2 m 이고, 통로를 돌아가야 하므로 실제 경로는
그보다 깁니다. 장면에 **책상은 하나뿐**입니다.

**로봇** — 몸통을 이미 작업 높이까지 내리고 고개를 39.8 도 숙인, 집기 직전 자세로 섭니다.
**바퀴가 바닥에 닿아 있습니다** — 공중에서 떨어지지도, 바닥을 뚫지도 않습니다. 돌리면
실제로 잰 바퀴 높이를 찍어 줍니다.

**카메라** — 채점이 정책에게 보내는 관측은 세 대입니다: 머리 `head_l`(672×376,
실기 ZED 좌안)과 양 손목 `wrist_l`/`wrist_r`(424×240, D405). 이 데모 스크립트는
아직 옛 구성을 스폰하며, 씬 생성기 교체와 함께 이 값으로 맞춰집니다. 과제 B 와 같습니다.

### 장면 하나는 seed 하나가 정합니다

`--seed` 가 같으면 어디서 몇 번을 돌려도 같은 장면입니다. 어느 좌석에서 시작하는지,
그리고 로봇이 쓰지 않는 나머지 탁상의 스툴이 어떻게 흩어지는지가 그 수에서 나옵니다.

```bash
--seed 1000        # 이 장면 (좌석 8)
--seed 1001        # 다른 장면
--seat 3           # 좌석을 직접 고릅니다 (0~11). 그냥 두면 seed 가 고릅니다
--check            # 좌석 기하와 매장 USD 만 검사하고 끝냅니다. Isaac Sim 을 안 띄워 1 초
```

### 장면을 글과 그림으로 받기

```bash
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_a_demo.py --seed 1000 --headless --seconds 1 \
    --scene-json /workspace/user/scene_a_1000.json \
    --shot /workspace/user/shot_a_1000.png
```

터미널에 좌석과 로봇 자세, 바구니 좌표, 목적지와 책상, 스툴 자리가 찍히고 같은 내용이
JSON 으로 남습니다. `--shot` 은 로봇 머리 카메라가 보는 그림을 한 장 저장합니다.
`/workspace/user` 는 호스트의 `workspace/` 라서 컨테이너 밖에서 바로 열립니다.

```
[장면] seed 1000, 좌석 8 (탁상 2 의 45도 자리)

  로봇 -- 좌석에서 앞으로 나와 탁상을 마주 본다
    자리      (-9.309, -1.459)  yaw -135.0 도
    탁상까지  중심에서 0.624 m (좌석은 0.924, 여기서 0.300 앞으로 나왔다)
    몸통      -0.0600    고개 39.8 도 아래

  집을 것 -- 탁상 위 파란 바구니
    바구니    (-9.609, -1.759, 0.750)  yaw +45.0 도
    ...

  가져갈 곳 -- 목적지 진열대와 그 옆 책상
    도착 자리 (-0.100, +2.559)  yaw +0.0 도
    책상      (+0.162, +1.698)  상판 0.725 m  -- 도착 자리에서 0.900 m
    직선거리  로봇에서 10.047 m (실제 경로는 통로를 돌아가므로 이보다 길다)
    ...
```

좌석 기하와 매장 USD 가 성한지는 Isaac Sim 을 띄우기 전에 `--check` 로 먼저 볼 수
있습니다. 좌석이 벽 안에 있거나 스툴이 회전을 막거나 매장 USD 가 없는 종류의 문제는
시뮬레이터 기동 60 초를 치르기 전에 알 수 있는 것들입니다.

### 좌표

바닥이 z = 0 입니다. 매장은 x 가 -11.1 ~ 1.3, y 가 -5.12 ~ 7.25 이고 **통로는 Y
방향**입니다. 시식 코너는 매장 서쪽(-X)에, 목표 진열대는 동쪽 끝(원점 근처)에
있습니다. 그래서 한 에피소드는 매장을 서에서 동으로 가로지릅니다.

옵션 전체와 더 자세한 설명은 [`scripts/README.md`](scripts/README.md) 에 있습니다.

## 과제 B 둘러보기

환경이 어떻게 생겼는지 보는 가장 빠른 길입니다. **에피소드가 시작되는 순간**을
만들어 세워 놓고 거기서 멈춥니다. 집지도, 놓지도, 움직이지도 않습니다. 여러분의
정책이 첫 관측으로 받게 될 그림을 그대로 보여 주는 것이 목적입니다.

```bash
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000
```

<br>

**진열대** — 다섯 단이 상품으로 차 있습니다. 그중 위 두 단(3단과 2단)의 앞줄에서
1~3 칸이 비어 있습니다. 비어 있는 칸 **뒤에는 그 칸에 들어갈 상품이 서 있습니다.**
무엇을 채워야 하는지는 진열대를 보면 알 수 있습니다.

**책상 위 파란 상자** — 빈 칸 수만큼 상품이 들어 있습니다. 상자의 첫 번째 상품이
첫 번째 빈 칸으로, 두 번째가 두 번째 빈 칸으로 갑니다.

**로봇** — 진열대를 마주 보고 **바퀴가 바닥에 닿은 채로** 섭니다. 공중에서 떨어지지
않습니다. 로봇 USD 의 정지 자세는 가장 낮은 바퀴를 0.3045 m 에 놓기 때문에, 그대로
두면 에피소드마다 218 mm 를 낙하하고 튄 자리에 서게 됩니다. 그래서 데모는 스폰 직후
바퀴 높이를 재서 그만큼 로봇을 내려 앉힙니다. 돌리면 그 숫자를 찍어 줍니다.

**카메라** — 채점이 정책에게 보내는 관측은 세 대입니다: 머리 `head_l`(672×376,
실기 ZED 좌안)과 양 손목 `wrist_l`/`wrist_r`(424×240, D405). 이 데모 스크립트는
아직 옛 구성을 스폰하며, 씬 생성기 교체와 함께 이 값으로 맞춰집니다.

### 장면 하나는 seed 하나가 정합니다

`--seed` 가 같으면 어디서 몇 번을 돌려도 같은 장면입니다. 어느 상품이 어느 칸에
서는지, 어느 칸이 비는지, 상자에 무엇이 담기는지가 모두 그 수에서 나옵니다.

```bash
--seed 1000        # 이 장면
--seed 1001        # 다른 장면
--gaps 1           # 빈 칸을 하나로 고정 (그냥 두면 seed 가 1~3 중에서 고릅니다)
```

### 장면을 글과 그림으로 받기

```bash
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000 --headless --seconds 1 \
    --scene-json /workspace/user/scene_1000.json \
    --shot /workspace/user/shot_1000.png
```

터미널에 진열대의 단·줄·칸별 상품과 좌표, 빈 칸, 상자 속 상품이 찍히고 같은 내용이
JSON 으로 남습니다. `--shot` 은 로봇 머리 카메라가 보는 그림을 한 장 저장합니다.
`/workspace/user` 는 호스트의 `workspace/` 라서 컨테이너 밖에서 바로 열립니다.

```
[장면] seed 1000, 빈 칸 3 개

  진열대 -- 단/줄/칸, 앞줄(row 0)이 손님 쪽
    3단  (판 높이 1.155 m)
      줄0 칸1  Chocobi snack box             (+0.568, -0.003, 1.224)  [chocobi]
      줄1 칸0  Buldak stir-fried noodle cup  (+0.734, -0.276, 1.213)  [samyang_buldak_cup]
      ...
  비어 있는 칸 -- 상자 속 i 번째 상품이 i 번째 칸에 들어간다
    0: 3단 줄0 칸2  <- Coca-Cola Zero can  [cocacola_zero]
    1: 3단 줄0 칸0  <- Buldak stir-fried noodle cup  [samyang_buldak_cup]
    2: 2단 줄0 칸1  <- small original Pringles tube  [pringles_original_small]

  상자 속 상품
    0: Coca-Cola Zero can            (-0.116, -0.821, 0.800)  [cocacola_zero]
    ...
```

상품에는 **이름**(`cocacola_zero`)과 **영어 표기**(`Coca-Cola Zero can`)가 둘 다
있습니다. 지시문에 쓰이는 것은 영어 표기 쪽입니다.

### 좌표

바닥이 z = 0 입니다. 진열대는 -X 를 보고 서 있고 그 **앞면이 x = 0.470** 입니다.
로봇은 원점 근처에서 진열대를 마주 봅니다. 책상과 상자는 로봇의 오른쪽(-Y)에
있습니다.

옵션 전체와 더 자세한 설명은 [`scripts/README.md`](scripts/README.md) 에 있습니다.

## 과제 B 한 판을 처음부터 끝까지 보기

위 `task_b_demo.py` 는 시작 장면에서 멈춥니다. 로봇이 실제로 어떻게 움직여서 상품을
꺼내고 진열대에 놓는지 보려면 `task_b_replay.py` 를 쓰세요. 미리 모아 둔 시연 일곱
판이 저장소에 함께 들어 있습니다.

```bash
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_replay.py --seed 1
```

호스트에서 한 줄로 띄우려면 `run/run_task_b_replay.sh` 를 쓰세요. `--seed 0` 부터
`--seed 6` 까지 일곱 판이고, 한 판은 107~273 초입니다. `--list` 로 목록을 봅니다.

**이것은 재생이지 시뮬레이션이 아닙니다.** 프레임마다 로봇의 관절과 상품의 위치를
기록에서 그대로 써 넣습니다. 로봇과 상품이 어디 있었는지는 정확하지만, 접촉은
보여 주지 못합니다 -- 상품이 손가락에 눌려 딸려 오는 것이 아니라 상품도 제자리에
놓입니다. 자세한 것은 [`scripts/README.md`](scripts/README.md) 에 있습니다.

## 환경 안의 에셋

이미지 안 `/workspace/assets` 에 있습니다(코드는 `source/cyclo_lab/data` 링크로
봅니다). 과제 A 와 B 를 세우는 데 필요한 것만 들어 있습니다.

```
data/
  robot/
    ffw_sg2.usd                      로봇 (40 MB)

  fixtures/                          집기 (456 KB)
    shelf/shelf.usd                    진열대. 재질 그림 네 장이 같은 폴더에
    table/table.usd                    책상
    crate/crate.usd                    파란 상자

  products/                          과제 B 의 상품 36 개 (196 MB)
    manifest.json                      크기, 무게, 콜라이더, USD 경로
    orientation.json                   어느 면이 위인가
    display_yaw.json                   진열될 때 몇 도 돌아가는가
    shapes.json                        상자인가 원통인가. 상자 안에서 눕는 모양을 정한다
    cocacola_zero/
      cocacola_zero.usd                  스폰되는 것
      cocacola_zero_skin.usd             보이는 메시와 재질
      textures/albedo.png                색 그림
    ... 35 개 더

  store/                             매장 (184 MB)
    manifest.json                      진열대·냉장고 20 종과 거기 놓이는 상품 35 종
    layout.json                        매장 배치
    eatin_measured.json                시식 코너 실측값. 12 좌석이 여기서 나온다
    destinations.json                  과제 A 의 목적지와 그 옆 책상 자리
    scene/                             매장 자체 -- 과제 A 가 스폰하는 USD
      fixture_kit/out/store_scene.usd    여기가 뿌리다
      fixture_kit/<킷>/assets/...        곤돌라·냉장고·냉동고·와인·시식 세트
      source/cyclo_lab/data/props/...    쇼케이스·계산대 등 맨 집기
```

앞의 둘은 매장을 **말로** 적은 것이고 `scene/` 은 매장 **자체**입니다. 과제 A 는
편의점을 가로지르므로 그림이 있어야 하고, 과제 B 는 진열대 하나만 세우므로 쓰지
않습니다(다만 환경 코드가 불러올 때 `manifest.json` 을 읽으므로 그것은 늘 들어 있습니다).
`products/` 와는 이름이 하나도 겹치지 않는 다른 집합입니다.

`scene/` 아래만 디렉토리 이름이 정리돼 있지 않은 데에는 이유가 있습니다. 매장 USD 는
레이어 94 개와 텍스처 180 장을 물고 있는데 그 274 개 경로가 **전부 상대경로**입니다.
서로의 위치 관계만 지키면 한 글자도 고치지 않고 통째로 옮겨지고, 반대로 이름을 정리하려면
그 274 개를 전부 다시 써야 하며 하나라도 놓치면 그 집기는 조용히 회색으로 나옵니다.
그래서 `scene/` 은 원본 저장소의 루트 자리를 대신하고, 그 아래는 원본 그대로입니다.

상품 USD 도 색 그림을 **자기 폴더 안에서 상대경로로** 찾습니다
(`./textures/albedo.png`). 그래서 상품 폴더 하나만 옮겨도 색이 그대로 따라옵니다.

## 화면으로 띄우기

```bash
./run/run_gui.sh
```

X11 구성을 겹쳐 컨테이너를 띄우고 **매장 기본 씬**(`scripts/basic_convstore.py`)을
자동으로 엽니다 — 편의점 매장 전체에 로봇이 서 있는 그림입니다. 로봇을 움직이는
것은 여러분의 코드 몫입니다. 창이 뜨기까지 30~60 초 걸리고 그동안 경고가 잔뜩
나옵니다. 정상입니다.

다른 씬을 보려면 컨테이너에 들어가 `--headless` 를 **빼고** 돌립니다. 창을 닫아도
컨테이너는 떠 있습니다.

```bash
docker exec -it challenge_env bash
# 예: 과제 B 데모 씬
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000
```

창이 안 뜨면 이 순서로 보세요. ① 컨테이너 안에서 `echo $DISPLAY` 가 비어 있지
않은지, ② 호스트에서 `xhost +local:root` 를 했는지, ③ Wayland 를 쓴다면 XWayland 가
돌고 있는지.

## 정책 서버와 제출

정책 서버 본보기(WebSocket + msgpack, 예시 정책 포함)와 내는 방법은 **대회
홈페이지**에서 안내합니다. 컨테이너가 `network_mode: host` 라서, 호스트에서 띄운
정책 서버가 컨테이너 안에서도 `127.0.0.1` 로 그대로 보입니다.

## 채점을 미리 돌려 보는 스크립트 (준비 중)

위 `task_a_demo.py` 와 `task_b_demo.py` 는 장면을 보여 줄 뿐 정책을 부르지 않습니다.
채점과 같은 방식으로 정책 서버를 붙여 돌려 볼 수 있는 스크립트를 준비하고 있습니다.
이런 흐름이 됩니다.

1. 여러분의 정책 서버를 호스트에서 띄운다
2. `scripts/` 의 스크립트가 컨테이너 안에서 환경을 띄우고, 채점 서버와 같은 방식으로
   관측을 보내고 동작을 받아 시뮬레이션을 진행한다
3. 끝나면 에피소드 요약을 찍는다

주고받는 형식이 정해지면 이 절과 `scripts/README.md` 를 고쳐 공지합니다.

## 라이선스 고지

이 저장소의 코드(스크립트·도커 구성)는 Apache-2.0 입니다 — 전문은 [`LICENSE`](LICENSE).

배포 이미지에 함께 들어가는 구성요소와 각각의 라이선스입니다. 대회 측이 따로 고친
구성요소는 없습니다(로봇 USD 는 원본 그대로 씁니다). 라이선스 전문은 이미지 안
`/workspace/cyclo_lab` 의 `LICENSE`, `LICENSE-IsaacLab`, `THIRD_PARTY_LICENSES.md`,
그리고 에셋 쪽은 `NOTICE_ASSETS.md` 에 들어 있습니다 — **레포 없이 이미지만 받아도
저작자 표시가 함께 갑니다.**

| 구성요소 | 라이선스 | 비고 |
|---|---|---|
| Isaac Sim (바탕 이미지) | [NVIDIA Isaac Sim Additional Software and Materials License](https://www.nvidia.com/en-us/agreements/enterprise-software/isaac-sim-additional-software-and-materials-license/) | 재배포 불가 조항 때문에 각자 NVIDIA 에서 직접 받습니다. `.env` 의 `ACCEPT_EULA=Y` 가 본인 동의 |
| Isaac Lab | BSD-3-Clause | 원본 그대로 |
| 대회 환경 코드 (cyclo_lab) | Apache-2.0 | ROBOTIS [robotis_lab](https://github.com/ROBOTIS-GIT/robotis_lab) 포크에 대회 환경을 얹은 것. 원저작권 고지는 코드에 유지 |
| ROBOTIS 로봇 모델 (FFW-SG2, [robotis_lab](https://github.com/ROBOTIS-GIT/robotis_lab)) | Apache-2.0 | 원본 USD 그대로 |
| whole_body_tracking 에서 가져온 코드 | MIT | `THIRD_PARTY_LICENSES.md` 에 고지 |
| 편의점 상품·집기 에셋 | 주최 측 제공 | 대회 참가 목적으로 사용 |
| 시식 코너 스툴 ([Cafe Table and Stools](https://sketchfab.com/3d-models/cafe-table-and-stools-95c4acc3eebc46419f833061b8b222e7)) | **CC BY 4.0** | 작가 **Guy in a Poncho** (Sketchfab). 과제 A 의 매장에 들어갑니다. `NOTICE_ASSETS.md` 에 고지 — **이 표기를 지우지 마세요** |
| 시식 코너 탁상 | 주최 측 제공 | 사내 CAD 에서 변환 |

## 문의

대회 홈페이지의 QnA 게시판을 이용해 주세요.
