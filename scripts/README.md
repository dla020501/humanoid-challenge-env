# scripts/ — 데모 스크립트

컨테이너의 `/workspace/challenge_scripts` 로 붙습니다. `git pull` 만 하면 컨테이너를
다시 만들지 않고 바로 돌릴 수 있습니다.

| 파일 | 하는 일 |
|---|---|
| `task_b_demo.py` | **과제 B 의 시작 장면**을 하나 만들어 띄웁니다 |

---

## `task_b_demo.py`

```bash
# 컨테이너 안에서
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000
```

창이 뜨고, 그 안에 과제 B 의 **에피소드가 시작되는 순간**이 서 있습니다. 여기서
멈춥니다. 집지도, 놓지도, 움직이지도 않습니다. 여러분의 정책이 첫 관측으로 받게 될
그림을 그대로 보여 주는 것이 목적입니다.

### 장면에 있는 것

**진열대** — 다섯 단이 상품으로 차 있습니다. 그중 위 두 단(3단과 2단)의 앞줄에서
1~3 칸이 비어 있습니다. 비어 있는 칸 **뒤에는 그 칸에 들어갈 상품이 서 있습니다.**
무엇을 채워야 하는지는 진열대를 보면 알 수 있습니다.

**책상 위 파란 상자** — 빈 칸 수만큼 상품이 들어 있습니다. 상자의 첫 번째 상품이
첫 번째 빈 칸으로, 두 번째가 두 번째 빈 칸으로 갑니다.

**로봇** — 진열대를 마주 보고 **바퀴가 바닥에 닿은 채로** 섭니다. 공중에서 떨어지지
않습니다. 로봇 USD 의 정지 자세는 가장 낮은 바퀴를 0.3045 m 에 놓기 때문에, 손대지
않으면 에피소드마다 218 mm 를 낙하하고 튄 자리에 서게 됩니다. 그래서 스폰 직후 실제
바퀴 높이를 재서 그만큼 로봇을 내려 앉힙니다(`settle_on_ground`). 돌리면 그 숫자를
찍어 줍니다.

**카메라** — 머리 하나(672×376)와 양 손목 둘(244×244). 채점 때 쓰는 값과 같습니다.

### 장면 하나는 seed 하나가 정합니다

`--seed` 가 같으면 어디서 몇 번을 돌려도 같은 장면입니다. 어느 상품이 어느 칸에
서는지, 어느 칸이 비는지, 상자에 무엇이 담기는지가 모두 그 수에서 나옵니다.

```bash
--seed 1000        # 이 장면
--seed 1001        # 다른 장면
--gaps 1           # 빈 칸을 하나로 고정 (그냥 두면 seed 가 1~3 중에서 고릅니다)
```

### 옵션

| 옵션 | 뜻 |
|---|---|
| `--seed N` | 장면을 정하는 수 (기본 1000) |
| `--gaps {1,2,3}` | 빈 칸 개수를 고정합니다 |
| `--seconds S` | S 초 동안 세워 두고 끝냅니다. 0 이면 창을 닫을 때까지 |
| `--headless` | 화면 없이 돌립니다 |
| `--scene-json FILE` | 장면 내용을 JSON 으로 저장합니다 |
| `--shot FILE.png` | 로봇 머리 카메라가 보는 그림을 한 장 저장합니다 |

### 장면을 글로 받기

```bash
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000 --headless \
    --seconds 1 --scene-json /workspace/user/scene_1000.json
```

터미널에 진열대의 단·줄·칸별 상품과 좌표, 빈 칸, 상자 속 상품이 찍히고 같은 내용이
JSON 으로 남습니다. `/workspace/user` 는 호스트의 `workspace/` 라서 컨테이너 밖에서
바로 열립니다.

```
[장면] seed 1000, 빈 칸 3 개

  진열대 -- 단/줄/칸, 앞줄(row 0)이 손님 쪽
    3단  (판 높이 1.155 m)
      줄0 칸1  Chocobi snack box             (+0.568, -0.003, 1.224)  [chocobi]
      줄1 칸0  Buldak stir-fried noodle cup  (+0.734, -0.276, 1.213)  [samyang_buldak_cup]
      줄1 칸1  Chocobi snack box             (+0.715, +0.004, 1.224)  [chocobi]
      줄1 칸2  Coca-Cola Zero can            (+0.761, +0.276, 1.220)  [cocacola_zero]
    2단  (판 높이 0.746 m)
      ...

  비어 있는 칸 -- 상자 속 i 번째 상품이 i 번째 칸에 들어간다
    0: 3단 줄0 칸2  <- Coca-Cola Zero can  [cocacola_zero]
    1: 3단 줄0 칸0  <- Buldak stir-fried noodle cup  [samyang_buldak_cup]
    2: 2단 줄0 칸1  <- small original Pringles tube  [pringles_original_small]

  상자 속 상품
    0: Coca-Cola Zero can            (-0.116, -0.821, 0.800)  [cocacola_zero]
    1: Buldak stir-fried noodle cup  (-0.280, -0.834, 0.789)  [samyang_buldak_cup]
    2: small original Pringles tube  (-0.436, -0.826, 0.788)  [pringles_original_small]

  상자 -0.282, -0.855, 0.727    책상 -0.282, -0.903    진열대 앞면 x = 0.470
```

상품에는 **이름**(`cocacola_zero`)과 **영어 표기**(`Coca-Cola Zero can`)가 둘 다
있습니다. 지시문에 쓰이는 것은 영어 표기 쪽입니다.

### 화면 없이 장면을 눈으로 보기

`--shot` 을 붙이면 로봇 머리 카메라가 보는 그림 한 장이 저장됩니다. 여러분의 정책이
첫 관측으로 받게 될 바로 그 그림입니다.

```bash
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000 --headless \
    --seconds 1 --shot /workspace/user/shot_1000.png
```

### 좌표

바닥이 z = 0 입니다. 진열대는 -X 를 보고 서 있고 그 **앞면이 x = 0.470** 입니다.
로봇은 원점 근처에서 진열대를 마주 봅니다. 책상과 상자는 로봇의 오른쪽(-Y)에
있습니다.

에셋이 어디에 어떤 이름으로 놓여 있는지는 루트 [`README.md`](../README.md) 의
**환경 안의 에셋** 절에 있습니다.
