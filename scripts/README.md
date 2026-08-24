# scripts/ — 데모 스크립트

컨테이너의 `/workspace/challenge_scripts` 로 마운트되어 있습니다. `git pull` 만 하면
컨테이너를 다시 만들지 않고 바로 실행됩니다.

| 파일 | 무엇을 하는가 |
|---|---|
| `task_b_demo.py` | **과제 B 의 시작 장면 하나**를 만들어 띄웁니다 |

---

## `task_b_demo.py` — 과제 B 의 시작 장면

```bash
# 컨테이너 안에서
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000
```

창이 뜨고, 그 안에 과제 B 의 **에피소드가 시작되는 순간**이 서 있습니다. 여기서
멈춥니다 — 집지도, 놓지도, 움직이지도 않습니다. 보여 주려는 것이 정책이 첫 관측으로
받게 될 바로 그 그림이기 때문입니다.

### 장면에 무엇이 있는가

* **진열대** — 다섯 단이 상품으로 차 있습니다. 그 중 위 두 단(3단·2단)의 앞줄에서
  1~3 칸이 비어 있습니다. **비어 있는 칸 뒤에는 그 칸에 들어가야 할 상품이 서 있습니다** —
  무엇을 채워야 하는지는 진열대를 보면 읽을 수 있습니다.
* **책상 위 파란 상자** — 빈 칸 수만큼 상품이 들어 있습니다. 상자의 *i* 번째 상품이
  *i* 번째 빈 칸에 들어갑니다.
* **로봇** — 진열대를 마주 보고, **바퀴가 바닥에 닿은 채로** 섭니다. 공중에서 떨어지지
  않습니다. 로봇 USD 의 정지 자세는 가장 낮은 구동 바퀴를 0.3045 m 에 놓기 때문에,
  그대로 두면 매 에피소드가 218 mm 낙하로 시작하고 튄 자리에 서게 됩니다. 스크립트는
  스폰 직후 실제 바퀴 높이를 재서 그만큼 루트를 내립니다 (`settle_on_ground`).
  실행하면 그 두 숫자를 찍어 줍니다.
* **카메라 셋** — 머리(672×376)와 양 손목(244×244). 수집 때 쓰는 값 그대로입니다.

### 한 장면은 seed 하나가 정합니다

`--seed` 가 같으면 어디서 몇 번을 돌려도 같은 장면입니다. 어느 상품이 어느 칸에 서는지,
어느 칸이 비는지, 상자에 무엇이 담기는지가 전부 그 수에서 나옵니다.

```bash
--seed 1000        # 이 장면
--seed 1001        # 다른 장면
--gaps 1           # 빈 칸을 1 개로 고정 (기본값은 seed 가 1~3 중에서 정합니다)
```

### 옵션

| 옵션 | 뜻 |
|---|---|
| `--seed N` | 장면을 정하는 수 (기본 1000) |
| `--gaps {1,2,3}` | 빈 칸 개수를 고정 |
| `--seconds S` | S 초 동안 유지하고 끝냅니다. 0 이면 창을 닫을 때까지 |
| `--headless` | 화면 없이 |
| `--shot FILE.png` | 로봇 머리 카메라가 보는 그림을 한 장 저장 |
| `--scene-json FILE` | 장면 내용을 JSON 으로 저장 |

### 화면 없이 장면 보기

GUI 를 띄우기 어려운 환경이라면 `--shot` 으로 머리 카메라의 그림을 받으면 됩니다.
여러분의 정책이 관측으로 받게 될 바로 그 화각입니다.

```bash
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000 --headless \
    --seconds 1 --shot /workspace/user/shot_1000.png
```
| `--shot FILE.png` | 로봇 머리 카메라가 보는 그림을 한 장 저장 (672×376) |

### 장면을 글로 받기

```bash
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000 --headless \
    --seconds 2 --scene-json /workspace/user/scene_1000.json
```

터미널에 진열대의 단·줄·칸별 상품과 좌표, 빈 칸, 상자 속 상품이 찍히고, 같은 내용이
JSON 으로 남습니다. `/workspace/user` 는 호스트의 `workspace/` 라서 컨테이너 밖에서
바로 열 수 있습니다.

```
[장면] seed 1000, 빈 칸 3 개

  진열대 -- 단/줄/칸, 앞줄(row 0)이 손님 쪽
    3단  (판 높이 1.156 m)
      줄0 칸1  Chilsung Cider can            (+0.567, -0.280, 1.216)  [chilsung_cider]
      ...
  비어 있는 칸 -- 상자 속 i 번째 상품이 i 번째 칸에 들어간다
    0: 3단 줄0 칸2  <- Coca-Cola Zero can  [cocacola_zero]
    ...
  상자 속 상품
    0: Coca-Cola Zero can            (-0.116, -0.821, 0.800)  [cocacola_zero]
```

상품에는 **이름**(`cocacola_zero`)과 **영어 표기**(`Coca-Cola Zero can`)가 둘 다 있습니다.
지시문이 쓰는 것은 영어 표기 쪽입니다.

### 화면 없이 장면을 눈으로 보기

`--shot` 을 붙이면 로봇 머리 카메라가 보는 그림 한 장이 저장됩니다 — 정책이 첫 관측으로
받게 될 바로 그 그림입니다.

```bash
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000 --headless \
    --seconds 1 --shot /workspace/user/shot_1000.png
```

### 좌표계

바닥이 z=0, 진열대는 -X 를 향해 서고 그 **앞면이 x = 0.470** 에 있습니다. 로봇은
원점 부근에서 진열대를 마주 봅니다. 책상과 상자는 로봇의 오른쪽(-Y)에 있습니다.
