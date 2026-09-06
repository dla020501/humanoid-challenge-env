# Humanoid Challenge — 참가자 환경 (로컬 개발용)

본 대회는 ROBOTIS의 **AI Worker (FFW-SG2)** 휴머노이드 로봇을 제어하여 편의점 업무를 수행하는 시뮬레이션 챌린지입니다. 
이 저장소(Repository)는 참가자들이 자신의 로컬 PC에서 실제 대회와 완전히 동일한 환경(Isaac Sim 5.1 / Isaac Lab 2.3)을 구축하고, 데이터를 수집하여 로봇 제어 정책(Policy)을 개발할 수 있도록 제공됩니다.

> **🚨 공식 채점 및 평가 방식 안내**  
> **공식 채점은 본 저장소(로컬 환경)가 아닌 주최 측 평가 서버에서 진행됩니다.**  
> **Humanoid Challenge Repo 목적:**  공식 채점 제출 기능이 포함되어 있지 않으며, 오직 참가자의 알고리즘 개발 및 사전 테스트 용도로만 사용됩니다.

> **📦 학습 데이터 공개**  
> 주최 측이 수집한 학습 데이터는 Hugging Face 에 있습니다:
> **https://huggingface.co/datasets/SSU-RealityLab/2026CS-Store-Challenge**

## 세 과제

| | Task | 하는 일 | 로봇 |
|---|---|---|---|
| **A** | 진열대로 이동 |  탁상에서 바구니를 집어, 장애물을 피해 목적지 진열대 옆 책상에 옮겨 놓는다 | 주행 및 정지 |
| **B** | 상품 진열 | 가져온 상자에서 상품을 꺼내 진열대의 빈 칸에 놓는다 | 주행 및 정지 |
| **C** | 인식과 계산 | 계산대의 상품을 하나씩 집으면서 무엇인지 알아보고 값을 더한다 | 정지 |

본 Repo에는 **세 과제의 장면**이 모두 들어 있습니다.

## 저장소 구성

```
docker/       도커 실행 구성. 환경 코드(cyclo_lab)와 에셋은 배포 이미지 안에 들어 있습니다
scripts/      주최측 제공 스크립트 — 씬 생성기(task 별)와 데모 평가 서버.
              컨테이너의 /workspace/challenge_scripts 로 붙습니다
  taskA/          과제 A 의 장면 정의 — 12 좌석, 목적지, 스툴, 진열, 실측값. 읽어 보셔도 됩니다
                  demos/ 는 정답 주행 세 판(전부 만점), stores/ 는 미리 구워 둔 진열 열두 벌.
                  task_a_replay.py 가 demos/ 를 틀고, task_a_demo.py 가 stores/ 를 씁니다
  taskB/          과제 B 의 채점기와 시연 기록 — taskb_score.py 가 평가표(상품 하나 15항목 30점)대로
                  채점하고, demos/ 는 시연 일곱 판. task_b_replay.py 가 둘 다 씁니다
  taskC/          과제 C 의 장면 정의(상품 8 종, 계산대 위 배치 규칙, 검사)와 시연 기록·채점기 — demos_gt/ 는
                  상품 3개 연속 정답 궤적 세 판, demos/ 는 품목별 한 판, scorer/ 는 평가표(상품 하나 5항목 17점) 채점기
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

- Ubuntu 22.04 (x86-64), NVIDIA GPU — **VRAM 8 GB 이상, 16 GB 이상 권장**
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

## Task A 환경 구성 및 실행 가이드

다음 명령어를 통해 Task A의 초기 시작 장면을 확인할 수 있습니다.

```bash
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_a_demo.py --seed 1000
```

### 1. 환경 주요 요소

* **매장:** 편의점 전체가 스폰됩니다. 통로 3줄, 곤돌라 12개, 냉장고, 냉동고, 와인 진열대, 계산대, 시식 코너로 구성됩니다. 진열대 하나 앞에서 진행되는 Task B·C와 달리, **Task A는 매장 전체를 가로지릅니다. 통로는 Y축 방향입니다.**
* **시식 탁상과 좌석:** 원형 탁상 3개를 4등분한 **12개의 고정 좌석** 중 한 곳에서 시작합니다. 로봇은 탁상을 정면으로 마주 본 상태로 스폰됩니다.
* **파란 바구니 (탁상 위):** 크기는 0.380 × 0.590 × 0.140 m이며, 긴 면이 로봇을 향하도록 놓입니다. **이 바구니를 집어서 옮기는 것이 과제입니다.**
* **목적지와 책상:** 목표 진열대 앞의 도착 지점과 그 옆의 책상입니다. 바구니는 이 책상 위에 놓여야 합니다. 좌석에 따라 직선거리 9.3 ~ 11.2 m이며, 통로를 우회해야 하므로 실제 경로는 이보다 깁니다. **장면 내 책상은 하나뿐입니다.**
* **로봇:** 몸통을 작업 높이까지 내리고 고개를 39.8도 숙인, 집기 직전 자세로 대기합니다. **바퀴가 바닥에 닿아 있으며**, 공중에 뜨거나 바닥을 뚫지 않습니다. 실행 시 실측된 바퀴 높이가 터미널에 출력됩니다.
* **관측 카메라:** 정책(Policy) 알고리즘이 시각 데이터로 활용할 카메라는 총 3대입니다. 로봇 머리에 장착된 `head_l` (672×376, ZED 좌안) 1대와 양 손목의 `wrist_l`, `wrist_r` (424×240, D405) 2대입니다. Task B와 동일합니다.

### 2. 좌석 번호 규칙

좌석은 시식 탁상 3개를 각각 4등분하여 **탁상 순서대로 0번부터 11번까지** 번호가 붙습니다.

| 구분 | 예시 | 활용 |
| --- | --- | --- |
| **좌석 번호** | `6` | `--seat` 옵션, JSON 데이터 내 `seat_id` 항목, 정답 주행 파일의 좌석 표기 |
| **탁상 · 각도** | `탁상 1의 225도 자리` | 터미널 출력 및 JSON 데이터 내 `seat.table_index` / `seat.seat_angle_deg` 항목 |

좌석 번호는 `--seed` 값으로 결정되며, 규칙은 아래와 같습니다.

```text
좌석 = (seed × 7919) % 12

seed   0   1   2   3   4   5   6   7   8   9  10  11
좌석   0  11  10   9   8   7   6   5   4   3   2   1
```

### 3. 환경 생성 파라미터 (`--seed`, `--seat`)

생성되는 씬(Scene)의 형태는 이 두 가지 옵션으로 결정됩니다.

* **`--seed` (환경 시드):** 고유한 장면 번호입니다. **`--seed` 값이 동일하면 언제 어디서 실행해도 100% 동일한 환경이 스폰됩니다.** 이 값이 결정하는 요소는 다음 네 가지입니다.

| 요소 | 무엇이 달라지는가 | 결정 방식 |
| --- | --- | --- |
| **좌석** | 로봇과 바구니가 12곳 중 어디서 출발하는가 | `(seed × 7919) % 12` |
| **목표 진열대** | 어떤 상품 21개가 서 있고 앞줄 어느 3칸이 비는가 | seed → 진열대 시드 |
| **기타 진열대** | 곤돌라 12개에 어떤 상품이 진열되는가 | seed → 매장 시드 → 12벌 중 1벌 |
| **스툴** | 로봇이 사용하지 않는 두 탁상의 스툴 8개 배치 | seed |

* **`--seat` (좌석 지정):** 0~11 중 하나를 직접 지정합니다. 생략하면 위 규칙에 따라 `--seed`가 좌석을 결정합니다.

> **진열대의 위치는 시드와 무관합니다.** 곤돌라·냉장고·계산대는 항상 같은 자리에 있으며, 달라지는 것은 선반에 진열된 상품뿐입니다. 즉 **장애물의 형상은 시드를 타지 않으므로 충돌 판정 조건은 모든 시드에서 동일**하고, 정책이 보게 되는 시각 정보만 매번 달라집니다.

* *참고:* 곤돌라 진열은 사전에 생성해 둔 12벌(`scripts/taskA/stores/`) 중 하나를 사용하므로, 어떤 장비에서 실행하더라도 동일한 시드는 동일한 진열을 스폰합니다.

### 4. Headless 모드를 활용한 빠른 데이터 추출

무거운 Isaac Sim 렌더링 창을 띄우지 않고도, 백그라운드에서 씬 정보를 빠르게 추출할 수 있습니다.

```bash
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_a_demo.py --seed 1000 --headless --seconds 1 \
    --scene-json /workspace/user/scene_a_1000.json \
    --shot /workspace/user/shot_a_1000.png
```

* **`--scene-json`:** 좌석 및 로봇 자세, 바구니 좌표, 목적지와 책상 위치, 스툴 배치, 그리고 **목표 진열대에 진열된 상품 21개의 좌표와 빈칸 위치**가 JSON 파일로 저장됩니다.
* **`--shot`:** 씬이 스폰된 순간 로봇의 머리 카메라(`head_l`) 시점을 PNG 이미지로 캡처합니다.
* **`--check`:** **Isaac Sim을 구동하지 않고 1초 만에** 12개 좌석의 기하 구조, 진열 상태, 매장 USD 존재 여부만 검사하고 종료합니다. 좌석이 벽에 묻히거나 스툴이 회전을 방해하거나 에셋이 누락되는 유형의 문제는, 시뮬레이터 기동에 드는 60초를 지불하기 전에 확인할 수 있습니다.

```text
  진열 -- seed 6
    목표 진열대  씨앗 227234  상품 21개, 빈 칸 [(3, 2), (2, 2), (3, 0)]
    기타 진열대  씨앗 691006  변주 12벌 중 store_v10

  판정: 문제 없음
```

> **Tip:** 저장 경로인 `/workspace/user`는 호스트 PC의 `workspace/` 폴더와 마운트되어 있으므로, 도커 컨테이너 밖에서도 추출된 파일들을 즉시 열어볼 수 있습니다.

### 5. Task A 데모 시연 재생 (Replay)

`task_a_demo.py`가 정지된 시작 화면만 보여준다면, `task_a_replay.py`는 로봇이 실제로 바구니를 집어 매장을 가로질러 책상에 내려놓는 전체 시연(Demo) 과정을 보여줍니다. 저장소에는 주최 측에서 미리 수집한 3개의 시연 데이터가 포함되어 있으며, **3개 모두 평가표 만점(6개 항목 21점 만점)** 입니다.

```bash
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_a_replay.py --seed 6
```

기록해 둔 궤적을 말 그대로 재생합니다. 로봇의 관절 각도와 베이스 위치, 바구니의 자세를 프레임마다 기록에서 그대로 읽어 씁니다. 물리 연산으로 다시 굴리는 것이 아니므로, 접촉이나 파지의 안정성은 이 화면이 답하는 질문이 아닙니다.

한 판은 세 구간이 이어진 형태이며(**1 집기 · 2 주행 · 3 놓기**), 현재 어느 구간인지 터미널에 실시간으로 출력됩니다.

```text
[i] 관절 31개를 이름으로 맞췄다 (기록 19 + 바퀴 6 + 집게 종속 6)
[i] 로봇 기울기 0.0도, 바퀴 높이 맞춤 z 1.4289
[토막] 1 pick      0.0 초
[토막] 2 carry    17.0 초
[토막] 3 place   161.9 초
[i] 끝. 로봇이 (-0.015, +2.166) 에 섰고 도착 자리까지 0.402 m 였습니다.
```

`--list` 옵션은 Isaac Sim을 구동하지 않고 1초 만에 수록된 판의 목록만 출력합니다.

#### 동봉된 데모 데이터 3종

| `--seed` | 좌석 | 프레임 | 길이 | 점수 | 구간 (집기/주행/놓기) |
| --- | --- | --- | --- | --- | --- |
| **0** | 0 | 1,473 | 147 초 | 21 / 21 | 170 / 1,034 / 269 |
| **2** | 10 | 1,353 | 135 초 | 21 / 21 | 170 / 911 / 272 |
| **6** | 6 | 1,893 | 189 초 | 21 / 21 | 170 / 1,449 / 274 |

`task_b_replay.py`의 `--seed`가 재생할 기록의 번호일 뿐인 것과 달리, **Task A의 `--seed`는 장면을 결정하는 값이면서 동시에 재생할 기록을 고르는 값입니다.** 즉 `task_a_demo.py --seed 6`과 `task_a_replay.py --seed 6`은 동일한 매장을 스폰합니다.

#### 재생 옵션

| 옵션 | 뜻 |
| --- | --- |
| `--seed N` | 재생할 판 (0 / 2 / 6, 기본값 6) |
| `--list` | 수록된 판의 목록만 출력하고 종료합니다. Isaac Sim을 구동하지 않습니다 |
| `--substeps N` | 기록 1프레임을 몇 단계로 나누어 그릴지 (기본값 4). 높일수록 부드럽고 느려집니다 |
| `--hz H` | 초당 렌더링 프레임 수 (기본값 40). 0이면 최고 속도로 재생합니다 |
| `--from_seconds S` | S초 지점부터 재생합니다. 놓기 구간만 보고 싶을 때 사용합니다 |
| `--as_recorded` | 진열을 **기록이 수집된 당시 그대로** 구성합니다 |
| `--headless` | 화면 없이 실행합니다 |

### 6. 좌표계

바닥이 z = 0입니다. 매장의 범위는 x가 -11.1 ~ 1.3, y가 -5.12 ~ 7.25이며 **통로는 Y축 방향**입니다. 시식 코너는 매장 서쪽(-X)에, 목표 진열대는 동쪽 끝(원점 부근)에 위치합니다. 따라서 한 에피소드는 매장을 서에서 동으로 가로지르는 형태가 됩니다.

옵션 전체와 더 자세한 설명은 [`scripts/README.md`](scripts/README.md)에 있습니다.

## Task B 환경 구성 및 실행 가이드

다음 명령어를 통해 Task B의 초기 시작 장면을 확인할 수 있습니다.

```bash
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000
```
### 1. 환경 주요 요소

* **진열대:** 총 5단이며, **작업 대상은 상단 2개 층(3단과 2단)입니다.** 이 두 층의 앞줄 중 **단 한 칸이 비어 있고**, 나머지 칸에는 상품이 서 있습니다.
* **파란 상자 (책상 위):** 진열대의 빈칸에 채워 넣을 목표 상품 1개가 들어 있습니다.
* **로봇:** 상자를 정면으로 마주 본 상태로 작업을 대기합니다.
* **관측 카메라:** 정책(Policy) 알고리즘이 시각 데이터로 활용할 카메라는 총 3대입니다. 로봇 머리에 장착된 `head_l` (672×376, ZED 좌안) 1대와 양 손목의 `wrist_l`, `wrist_r` (424×240, D405) 2대입니다.

### 2. 상품 명명 규칙
상품 데이터는 시스템 내부용과 지시문용 두 가지 이름으로 관리됩니다.

| 구분 | 예시 | 활용 |
| --- | --- | --- |
| **코드용 이름** | `pringles_original_small` | 상품 폴더 및 USD 파일명, `manifest.json` 등 설정 파일의 Key값, JSON 데이터 내 `product` 항목 |
| **영어 이름** | `small original Pringles tube` | 로봇에게 하달되는 자연어 지시문(Language Instruction), JSON 데이터 내 `label` 항목 |

### 3. 환경 생성 파라미터 (`--gaps`, `--seed`)

생성되는 씬(Scene)의 형태는 이 두 가지 옵션으로 결정됩니다. 두 값 중 하나만 변경되어도 완전히 다른 환경(빈칸 위치, 상품 종류 등)이 구성됩니다.

* **`--gaps` (빈칸 개수):** 진열대에서 비워둘 칸의 수를 정합니다. 1, 2, 3 중 하나를 선택할 수 있으며, **참가자들이 실제 평가받는 환경의 기본값은 1입니다.**
* *참고:* 빈칸 하나당 상자 안의 목표 상품 하나가 매칭됩니다. 값을 2로 설정하면 로봇은 두 번의 진열 작업을 수행해야 합니다. (동일한 열에서 두 칸이 동시에 비거나, 상자에 동일한 상품이 중복 생성되지는 않습니다.)

* **`--seed` (환경 시드):** 고유한 장면 번호입니다. `--gaps`와 `--seed` 값이 동일하면 언제 실행해도 100% 동일한 환경이 스폰됩니다.

### 4. Headless 모드를 활용한 빠른 데이터 추출

무거운 Isaac Sim 렌더링 창을 띄우지 않고도, 백그라운드에서 씬 정보를 빠르게 추출할 수 있습니다.

```bash
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000 --headless --seconds 1 \
    --scene-json /workspace/user/scene_1000.json \
    --shot /workspace/user/shot_1000.png
```

* **`--scene-json`:** 진열대 내 모든 상품의 좌표, 빈칸 위치, 상자 속 타겟 상품 정보가 JSON 파일로 저장됩니다.
* **`--shot`:** 씬이 스폰된 순간 로봇의 머리 카메라(`head_l`) 시점을 PNG 이미지로 캡처합니다.

> **Tip:** 저장 경로인 `/workspace/user`는 호스트 PC의 `workspace/` 폴더와 마운트되어 있으므로, 도커 컨테이너 밖에서도 추출된 파일들을 즉시 열어볼 수 있습니다.

### 5. Task B 데모 시연 재생 (Replay)

`task_b_demo.py`가 정지된 시작 화면만 보여준다면, `task_b_replay.py`는 로봇이 실제로 상품을 꺼내 진열하는 전체 시연(Demo) 과정을 보여줍니다. 저장소에는 주최 측에서 미리 수집한 7개의 시연 데이터가 포함되어 있습니다.

```bash
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_replay.py --seed 1
```

기록해 둔 궤적을 말 그대로 재생합니다. 로봇의 관절 각도와 상품의 위치를 프레임마다
기록에서 그대로 읽어 씁니다.

### 6. 재생 중 실시간 채점 시스템

과제 B의 평가는 **상품 1개당 15개 항목, 총 30점 만점**으로 구성됩니다. 시연 재생 스크립트를 실행하면 내부적으로 `scripts/taskB/taskb_score.py`가 연동되어, 특정 채점 조건을 달성하는 즉시 터미널에 실시간 로그를 출력합니다.

```text
[점수] 채점 대상 samyang_buldak_cup → 목표 칸 L2 c2 · 평가표 15항목 30점
[점수]    8.3초  product 에 닿았는가             +1   누적  1/30
[점수]   10.3초  product 를 들어올렸는가           +2   누적  3/30
[점수]   10.4초  product 를 상자 밖으로 꺼냈는가      +3   누적  6/30
   ...
[점수]  113.3초  ── 놓은 뒤 3초 ──
[점수]          어느 칸에 넣었는가                 +4/4   칸 (2, 2) 좌우 -3 mm
   ...
[점수] ════ 최종 29 / 30 점 ════

```

#### 채점 판정 방식

채점은 크게 다음 두 가지 방식으로 나뉩니다.

1. **최초 1회 달성 (Event-triggered)**
* **항목:** 상품 터치, 들어 올림, 상자 밖으로 꺼냄, 진열대 앞 도달, 목표 층 도달, 목표 칸 앞 도달
* **판정:** 에피소드가 진행되는 동안 해당 조건을 최초로 만족하는 순간 즉시 점수가 부여되며, 이후 상태가 변하더라도 부여된 점수는 회수되지 않습니다.


2. **그리퍼 개방 3초 후 상태 (State-check)**
* **항목:** 떨어뜨리지 않음, 정확한 목표 층/칸, 서 있는 자세(Upright), 방향, 앞줄 정렬, 정지 상태, 상자 제자리 유지, 기존 상품 훼손 없음
* **판정:** 로봇의 그리퍼(손)가 열린 시점으로부터 **정확히 3초 뒤의 상태**를 확인하여 단 한 번만 평가합니다.



> 🚨 **평가 조기 종료 조건 — 상품을 떨어뜨린 경우**
> 상자에서 꺼낸 상품이 **바닥에 떨어지면 그 시점에 에피소드 채점이 종료**됩니다. 떨어뜨린 상품을 다시 주워 진열해도 점수는 오르지 않습니다. 종료 시점까지 획득한 누적 점수만 최종 점수로 인정되며, 별도의 감점 제도는 없습니다.

#### 동봉된 데모 데이터 7종 채점 결과

(기본 내장된 채점기로 측정한 기준입니다)

| `--seed` | 타겟 상품 | 최종 점수 | 못 받은 항목 |
| --- | --- | --- | --- |
| **0** | Buldak stir-fried noodle cup | 29 / 30 | 방향 (뒷줄 상품과 yaw 107° 틀어짐) |
| **1** | small sour cream Pringles tube | 30 / 30 | - |
| **2** | Yegam original potato chip tube | 30 / 30 | - |
| **3** | baked sweet potato snack box | 30 / 30 | - |
| **4** | Jin Ramen hot cup | 30 / 30 | - |
| **5** | Butter Ring biscuit box | 27 / 30 | 자세 (178° 뒤집힘), 방향 |
| **6** | Cereal Choco biscuit box | 27 / 30 | 자세 (179° 뒤집힘), 방향 |

#### 채점기 단독 실행 (Standalone)

채점 스크립트(`taskb_score.py`)는 Isaac Sim 시뮬레이터 구동 없이, Numpy 환경만 구성되어 있다면 기록된 `.npz` 파일을 통해 독립적으로 실행해 볼 수 있습니다.

```bash
python3 scripts/taskB/taskb_score.py scripts/taskB/demos/demo_00.npz
```

*각 평가 항목별 구체적인 측정 방식과 임계값(Threshold) 수치는 해당 파이썬 파일 내부의 `RUBRIC` 및 `THRESHOLD` 변수, 그리고 `scripts/README.md` 문서에서 상세히 확인할 수 있습니다.*

> ⚠️ **채점 항목과 가점 기준은 변할 수 있습니다.**
> 위 채점기와 동봉된 데모 데이터는 **예시 파일**입니다. 변동이 있으면 오픈 카카오톡 방과 대회 사이트에 공지하겠습니다.


## Task C 환경 구성 및 실행 가이드

다음 명령어를 통해 Task C의 초기 시작 장면을 확인할 수 있습니다.

```bash
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_c_demo.py --seed 1000
```
### 1. 환경 주요 요소

* **매장과 계산대:** Task A와 같은 편의점 전체가 스폰되며, 작업은 매장 남서쪽 **계산대** 앞에서 이루어집니다. Task C는 정지 과제이므로 로봇은 주행하지 않습니다.
* **빨간 띠 (계산대 상판):** 상판(높이 0.9035 m) 위, 로봇 기준 앞 11~50 cm · 왼쪽 -1~57 cm 영역에 폭 20 mm의 빨간 테이프 띠가 그려져 있습니다. **상품은 모두 이 띠 안에서만 스폰됩니다.**
* **상품 3개:** 대상 상품 8종 가운데 시드가 고른 3개가 띠 안에 놓입니다. **슬롯 0이 집어야 할 목표 상품**이고 나머지 2개는 배경입니다. 3개 모두 **QR 면이 로봇의 정 우측(월드 -Y)을 향하며**, 원통형 상품(프링글스·컵라면·캔)은 세워서, 상자형 상품(예감·롯데샌드)은 눕혀서 놓입니다. 상품 표면 간 간격은 10 cm 이상이 보장됩니다.
* **스캐너:** 로봇 오른손이 드는 위치에 중력 없이 떠 있습니다. 집은 상품의 QR 코드를 이 스캐너에 비추는 것이 과제이며, 데모는 스캐너를 그 자리에 두는 데서 멈춥니다.
* **로봇:** 계산대를 정면으로 마주 본 상태로 작업을 대기합니다. 몸통 리프트 0.0 m, 고개 39.8° 숙임, 양팔 스토우 자세이며 바퀴는 바닥에 닿아 있습니다.
* **관측 카메라:** 정책(Policy) 알고리즘이 시각 데이터로 활용할 카메라는 총 3대입니다. 로봇 머리에 장착된 `head_cam` (672×376, ZED 좌안) 1대와 양 손목의 `left_wrist_cam`, `right_wrist_cam` (424×240, D405) 2대입니다.

### 2. 상품 명명 규칙
상품 데이터는 Task B와 같이 시스템 내부용과 지시문용 두 가지 이름으로 관리됩니다.

| 구분 | 예시 | 활용 |
| --- | --- | --- |
| **코드용 이름** | `pringles_original_small` | 상품 폴더 및 USD 파일명(`<이름>_phys.usd`), `products.json` 등 설정 파일의 Key값, JSON 데이터 내 `product` 항목, `--products` 옵션 |
| **영어 이름** | `small original Pringles tube` | 로봇에게 하달되는 자연어 지시문(Language Instruction), JSON 데이터 내 `label` 항목 |

Task C의 대상 상품 8종은 다음과 같습니다.

| 코드용 이름 | 영어 이름 | 형상 |
| --- | --- | --- |
| `pringles_original_small` | small original Pringles tube | 원통 |
| `pringles_sourcream_small` | small sour cream Pringles tube | 원통 |
| `ottogi_cupnoodle_buldak` | Ottogi Buldak cup noodle | 원통 |
| `samyang_buldak_cup` | Buldak stir-fried noodle cup | 원통 |
| `chilsung_cider` | Chilsung cider can | 원통 |
| `cocacola_zero` | Coca-Cola zero can | 원통 |
| `yegam_original` | Yegam original potato chip tube | 상자 |
| `lotte_sand` | Lotte Sand biscuit box | 상자 |

### 3. 환경 생성 파라미터 (`--seed`, `--products`)

생성되는 씬(Scene)의 형태는 `--seed` 하나로 결정됩니다. 어떤 상품 3개가 오는지, 각 상품이 띠 안 어느 위치에 어떤 자세로 놓이는지가 모두 이 값에서 나옵니다.

* **`--seed` (환경 시드):** 고유한 장면 번호입니다. 값이 동일하면 언제, 어느 컴퓨터에서 실행해도 100% 동일한 환경이 스폰됩니다. **0·1·2는 평가 표본 시드**로, 주최 측 정답 궤적(`cstore-challenge` 저장소 `ship/ground_truth_sample/`의 세 판)과 같은 장면이 스폰됩니다. 이때는 딜하지 않고 `scripts/taskC/samples/scene_<n>.json`에 담긴 정착된 배치를 그대로 세우므로 정답 궤적과 mm 단위까지 같은 자리입니다(원 시드 3015066000·3050039000·4156003000).
* **`--scene-file` (장면 파일):** 딜하지 않고 주어진 장면 JSON(`--scene-json` 출력이나 정답 표본의 `scene.json`)의 상품 자세를 그대로 세웁니다. 정답 궤적을 재생하거나 채점 로직을 맞춰 볼 때 씁니다.
* **`--products` (상품 지정):** 코드용 이름 3개를 쉼표로 주면 시드가 고르는 대신 그 상품 3개를 사용합니다. **첫 번째가 목표 상품**입니다. (예: `--products cocacola_zero,lotte_sand,yegam_original`)
* *참고:* 상품은 스폰 뒤 3초간 물리로 안정화되며, 띠를 벗어나거나 넘어지거나 QR 방위가 3° 이상 틀어지거나 간격이 10 cm 미만이면 같은 시드 안에서 자동으로 재배치(최대 50회)합니다. 따라서 출력되는 좌표는 스폰 값이 아니라 **안정화된 뒤 실제로 측정한 값**입니다.

### 4. Headless 모드를 활용한 빠른 데이터 추출

무거운 Isaac Sim 렌더링 창을 띄우지 않고도, 백그라운드에서 씬 정보를 빠르게 추출할 수 있습니다.

```bash
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_c_demo.py --seed 1000 --headless --seconds 1 \
    --scene-json /workspace/user/scene_c_1000.json \
    --shot /workspace/user/shot_c_1000.png
```

* **`--scene-json`:** 상품 3개의 이름·좌표(월드/로봇 좌표)·자세, 빨간 띠, 로봇 시작 자세, 스캐너 위치, 카메라 해상도가 JSON 파일로 저장됩니다.
* **`--shot`:** 씬이 스폰된 순간 로봇의 머리 카메라(`head_cam`) 시점을 PNG 이미지로 캡처합니다.
* **`--check`:** Isaac Sim을 띄우지 않고 상품 8종의 USD·QR 타일 정보·스캐너·매장 USD가 제자리에 있는지와 띠 기하만 검사하고 종료합니다(1초 소요). 문제가 있으면 `!`로 시작하는 줄로 출력되고 종료 코드가 1이 됩니다.

> **Tip:** 저장 경로인 `/workspace/user`는 호스트 PC의 `workspace/` 폴더와 마운트되어 있으므로, 도커 컨테이너 밖에서도 추출된 파일들을 즉시 열어볼 수 있습니다.

터미널에는 JSON과 같은 내용이 다음과 같이 출력됩니다.

```text
[장면] seed 1000, 집을 것 small original Pringles tube [pringles_original_small]

  로봇 -- 계산대를 마주 보고 선다 (정지 과제: 주행하지 않는다)
    자리      (-3.449, -4.274)  yaw +90.0 도
    몸통      +0.0000    고개 39.8 도 아래    양팔 스토우 (오른팔 joint1 1.200)
    계산대    중심 (-4.000, -4.220)  상판 0.9035 m

  계산대 위 상품 -- 슬롯 0 이 집을 상품, QR 면은 정 오른쪽(-Y)을 본다
    0: small original Pringles tube     (-3.877, -3.853, 0.954)  [pringles_original_small] 직립  QR 오차 0.0 도  최근접 13.3 cm
    1: Lotte Sand biscuit box           (-3.496, -3.941, 0.927)  [lotte_sand] 눕힘  QR 오차 0.0 도  최근접 31.7 cm
    2: small sour cream Pringles tube   (-3.950, -4.075, 0.954)  [pringles_sourcream_small] 직립  QR 오차 0.0 도  최근접 13.3 cm

  빨간 띠(로봇 좌표)  x 0.110~0.500  y -0.010~0.570  테이프 20 mm  -- 상품끼리 10 cm 이상
  스캐너    오른손이 드는 자리 (-3.292, -3.940, 1.161)  크기 0.067 x 0.161 x 0.087 m
  카메라    head_cam 672x376, left_wrist_cam 424x240, right_wrist_cam 424x240
  재딜      0 회
```

### 5. Task C 데모 시연 재생 (Replay)

`task_c_demo.py`가 정지된 시작 화면만 보여준다면, `task_c_replay.py`는 로봇이 실제로 계산대의 상품을 집어 스캐너에 비추고 제자리에 내려놓는 전체 시연(Demo) 과정을 보여줍니다. 저장소에는 주최 측에서 미리 수집한 11개의 시연 데이터가 두 묶음으로 포함되어 있습니다.

| 묶음 | 내용 | 편 수 | 위치 |
| --- | --- | --- | --- |
| **`--set gt`** | 평가와 같은 형식 — 한 판에 **상품 3개를 차례로** 처리하는 정답 궤적 | 3편 (`--seed 0·1·2`) | `scripts/taskC/demos_gt/` |
| **`--set single`** | 학습 데이터와 같은 형식 — 한 판에 **상품 1개**를 처리 | 8편 (품목별 1편) | `scripts/taskC/demos/` |

```bash
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_c_replay.py --set gt --seed 0
```

Task A·B 재생기가 기록된 자세를 프레임마다 그대로 써 넣는 것과 달리, Task C 재생기는 **기록된 관절 명령(`actions.npy`, 22채널, 30 Hz)을 그때와 같은 주기로 로봇에게 다시 주고 물리가 상품을 움직이게 합니다.** 기록에 상품의 자세가 없기 때문입니다. 시작 장면과 물리가 같으므로 상품이 그때처럼 손에 딸려 오고, 스캐너 앞을 지나고, 띠 안에 놓입니다. 접촉이 실제로 일어나므로 파지가 버티는지도 이 화면이 답합니다.

한 판은 상품마다 여덟 국면이 이어진 형태이며(**접근 · 파지 · 들어올림 · 스캔 스윕 2회 · 내려놓기 · 후퇴 · 복귀**), 현재 어느 국면인지 터미널에 실시간으로 출력됩니다. 재생이 끝나면 상품별로 최대 들림·스캐너 최근접 거리·최종 위치(띠 안/밖)를 출력하고, `--summary-json`으로 저장할 수 있습니다.

```text
[재생] ottogi_cupnoodle_buldak_0  상품 ottogi_cupnoodle_buldak -> yegam_original -> samyang_buldak_cup  9242 프레임 (308.1 초 @ 30 Hz)
[재생]    3.4초  국면 s0_grasp
[재생]   11.0초  국면 s0_sweep_00
   ...
[재생] 끝. 상품별 결과 (로봇 좌표, 기록의 첫 프레임 기준)
  0: ottogi_cupnoodle_buldak    최대 들림  231.3 mm  스캐너 최근접  172.2 mm (f669)   최종 자리 (+0.440, +0.114, 0.954) 띠 안  들어올림 O
  1: yegam_original             최대 들림  226.5 mm  스캐너 최근접  229.4 mm (f3171)  최종 자리 (+0.446, +0.376, 0.931) 띠 안  들어올림 O
  2: samyang_buldak_cup         최대 들림  235.7 mm  스캐너 최근접  156.5 mm (f7997)  최종 자리 (+0.227, +0.079, 0.958) 띠 안  들어올림 O
```

`--list` 옵션은 Isaac Sim을 구동하지 않고 1초 만에 수록된 판의 목록만 출력합니다.

#### 동봉된 데모 데이터 11종

기록 한 편은 폴더 하나입니다. `joints.npy`·`actions.npy` (T, 22) float32 — 왼팔 7 · 왼 그리퍼 1 · 오른팔 7 · 오른 그리퍼 1 · 머리 2 · 리프트 1 · 예비 3, `timestamps.npy` (T,) 초, `phases.json` (국면 경계 프레임), `meta.json` (상품·시드·등급·지시문), `taskC_qr_scene_<시드>.json` (시작 장면), 초기 3캠 JPG. 카메라 프레임 전체는 크기 때문에 저장소에 없습니다.

| `--set gt --seed` | 슬롯 0 → 1 → 2 | 프레임 | 길이 |
| --- | --- | --- | --- |
| **0** | 오뚜기 컵누들 불닭 → 예감 오리지널 → 삼양 불닭 컵 | 9,242 | 308초 |
| **1** | 삼양 불닭 컵 → 오뚜기 컵누들 불닭 → 예감 오리지널 | 7,567 | 252초 |
| **2** | 삼양 불닭 컵 → 예감 오리지널 → 오뚜기 컵누들 불닭 | 8,236 | 275초 |

| `--set single --seed` | 상품 | 프레임 | 길이 |
| --- | --- | --- | --- |
| **0** | 프링글스 오리지널 (소) (`pringles_original_small`) | 3,099 | 103초 |
| **1** | 프링글스 사워크림 (소) (`pringles_sourcream_small`) | 2,849 | 95초 |
| **2** | 오뚜기 컵누들 불닭 (`ottogi_cupnoodle_buldak`) | 1,928 | 64초 |
| **3** | 예감 오리지널 (`yegam_original`) | 1,983 | 66초 |
| **4** | 삼양 불닭 컵 (`samyang_buldak_cup`) | 2,703 | 90초 |
| **5** | 칠성사이다 캔 (`chilsung_cider`) | 2,731 | 91초 |
| **6** | 코카콜라 제로 캔 (`cocacola_zero`) | 2,097 | 70초 |
| **7** | 롯데샌드 (`lotte_sand`) | 2,268 | 76초 |

`--set gt`의 `--seed`는 Task A와 같이 **장면을 결정하는 값이면서 동시에 재생할 기록을 고르는 값입니다.** 즉 `task_c_demo.py --seed 0`과 `task_c_replay.py --set gt --seed 0`은 동일한 계산대 장면을 스폰합니다. 반면 `--set single`의 `--seed`는 Task B와 같이 재생할 기록의 번호일 뿐이며, 장면은 기록에 동봉된 `taskC_qr_scene_<시드>.json`에서 옵니다.

동봉된 기록은 모두 수집 파이프라인에서 성공(등급 CLEAN, 스캐너 인식 1회 이상, 띠 안 배치)한 판입니다. 이 재생기로 다시 돌려 상품이 들려 스캐너 앞까지 갔다가 띠 안 제자리로 돌아오는 것까지 확인한 편은 `gt` 시드 0과 `single` 시드 6(코카콜라)이며, `single` 시드 5(칠성사이다 캔)는 재생에서 파지가 재현되지 않아 다른 기록으로 교체할 예정입니다.

#### 재생 옵션

| 옵션 | 뜻 |
| --- | --- |
| `--set gt` / `--set single` | 재생할 묶음 (기본값 gt) |
| `--seed N` | 그 묶음에서 재생할 판 (gt 0·1·2, single 0~7, 기본값 0) |
| `--list` | 수록된 판의 목록만 출력하고 종료합니다. Isaac Sim을 구동하지 않습니다 |
| `--episode DIR` | 묶음 대신 기록 폴더를 직접 지정합니다 |
| `--substeps N` | 기록 1프레임을 몇 단계의 물리 스텝으로 잇는지 (기본값 4 = 기록과 같은 속도) |
| `--no-interp` | 이웃 프레임 사이의 명령을 선형으로 채우지 않습니다 |
| `--frames N` | 앞에서 N 프레임만 재생합니다 (0이면 전부) |
| `--start-hold S` | 첫 프레임 자세로 S초 세워 둔 뒤 시작합니다 (기본값 1.0) |
| `--summary-json FILE` | 상품별 결과를 JSON 파일로 저장합니다 |
| `--headless` | 화면 없이 실행합니다 |

### 6. Task C 채점기 (Standalone)

평가 기준(상품 1개당 5개 항목 17점: 파지 2 · 들어올림 2 · 스캐너 조준 3 · QR 인식 7 · 띠 안 배치 3)을 코드로 옮긴 채점기가 `scripts/taskC/scorer/`에 있습니다. 시뮬 루프 안에서 매 스텝 관측을 콜백으로 받아 판정하며(`taskc_scorer.py`), Isaac 없이 numpy만으로 돌아가는 자체 검증이 함께 있습니다.

```bash
python3 scripts/taskC/scorer/selftest.py      # 기하·시나리오·규정 준수 35개 검사
```

평가 기준 원문과 미확정 항목(제한 시간, 총점 표기)은 `scripts/taskC/scorer/EVALUATION_DRAFT.md`에, 콜백 배선 방법은 `scripts/taskC/scorer/README.md`에 있습니다. **재생 중 실시간 채점(`[점수]` 출력)은 준비 중**이며, 채점 기준은 확정 과정에서 바뀔 수 있습니다.

### 7. 좌표계

바닥이 z = 0이며 매장 좌표는 Task A와 동일합니다. 계산대 중심은 (-4.00, -4.22), 로봇은 그 앞 (-3.45, -4.27)에서 +Y 방향을 바라봅니다. 장면 JSON의 상품 좌표는 월드 좌표(`pos`)와 로봇 좌표(`pos_robot`: x 앞, y 왼쪽) 두 가지로 제공됩니다.

옵션 전체와 더 자세한 설명은 [`scripts/README.md`](scripts/README.md)에 있습니다.

## 환경 에셋 (Assets) 구조

시뮬레이션 환경 구성에 필요한 에셋은 도커 이미지 내 `/workspace/assets` 경로에 위치하며, 코드 상에서는 `source/cyclo_lab/data` 심볼릭 링크를 통해 접근합니다. 이 폴더에는 **Task A·B·C**를 실행하는 데 필요한 필수 에셋만 경량화되어 포함되어 있습니다.

```text
data/
  ├── robot/                 # 로봇 에셋 (40 MB)
  │   └── ffw_sg2.usd          # 로봇 원본 USD
  │
  ├── fixtures/              # 매장 집기 에셋 (456 KB)
  │   ├── shelf/shelf.usd      # 진열대 (동일 폴더 내 재질 이미지 4장 포함)
  │   ├── table/table.usd      # 목적지 옆 책상
  │   ├── crate/crate.usd      # 파란 상자
  │   └── scanner/scanner_taskC.usd  # 과제 C 바코드 스캐너
  │
  ├── products/              # 과제 B 목표 상품 36종 (196 MB)
  │   ├── manifest.json        # 상품별 크기, 무게, 콜라이더, USD 경로 정보
  │   ├── orientation.json     # 상품별 상단(Up-face) 정의
  │   ├── display_yaw.json     # 진열 시 기본 회전 각도(Yaw)
  │   ├── shapes.json          # 형태(상자형/원통형) 구분 및 상자 내 배치 형태 정의
  │   └── cocacola_zero/       # 개별 상품 디렉토리 예시 (총 36종)
  │       ├── cocacola_zero.usd       # 시뮬레이션에 스폰되는 최상위 USD
  │       ├── cocacola_zero_skin.usd  # 시각적 메시(Mesh) 및 재질(Material)
  │       └── textures/albedo.png     # 텍스처 이미지
  │
  ├── products_c/            # 과제 C 목표 상품 8종 (39 MB) — QR 타일이 붙은 별도 파일
  │   ├── products.json        # 이름·가격·QR 타일 위치
  │   ├── _qr_tiles.json       # 타일 법선과 크기
  │   ├── taskC_products.json  # 크기·콜라이더
  │   ├── taskC_barcodes.json  # QR 면의 꼭짓점
  │   └── cocacola_zero/       # 개별 상품 디렉토리 예시 (총 8종)
  │       ├── cocacola_zero_phys.usd  # 시뮬레이션에 스폰되는 USD (옆의 .usdc·텍스처를 상대참조)
  │       ├── cocacola_zero.usdc      # 메시와 재질
  │       └── cocacola_zero.png       # 텍스처 이미지
  │
  └── store/                 # 과제 A 매장 환경 (184 MB)
      ├── manifest.json        # 매장 내 진열대·냉장고 20종 및 배치 상품 35종 정보
      ├── layout.json          # 매장 전체 레이아웃
      ├── eatin_measured.json  # 시식 코너 실측 데이터 (12개 시작 좌석 생성 기준)
      ├── destinations.json    # 과제 A 목적지 진열대 및 책상 위치 정보
      └── scene/               # 과제 A에 스폰되는 매장 전체 3D 씬 (USD)
          ├── fixture_kit/out/store_scene.usd  # 매장 씬의 최상위(Root) 경로
          ├── fixture_kit/<킷>/assets/...      # 곤돌라, 냉동고, 와인, 시식 세트 등
          └── source/cyclo_lab/data/props/...  # 쇼케이스, 계산대 등 단일 집기 에셋

```

### `store/` 와 `products/` 의 차이점

* `store/` 내의 `.json` 파일들이 매장의 구성을 텍스트(데이터)로 정의한다면, `scene/` 디렉토리는 렌더링에 사용되는 매장 환경 자체입니다.
* 편의점 전체를 이동해야 하는 **과제 A**에서는 이 `scene/` 매장 전체가 스폰되지만, 단일 진열대만 사용하는 **과제 B**에서는 이 매장 씬을 쓰지 않습니다. (단, 과제 B 환경 초기화 시에도 `manifest.json`은 공통으로 참조합니다.)
* `store/` 에셋과 `products/` 에셋은 파일명이나 구성이 겹치지 않는 완전히 별개의 데이터셋으로 분리되어 있습니다.

### 디렉토리 구조가 원본 그대로 보존된 이유 (상대 경로 설계)

`store/scene/` 하위 디렉토리의 구조가 다소 복잡하게 유지되는 것에는 기술적인 이유가 있습니다.

매장 USD 파일은 94개의 레이어와 180장의 텍스처 등 총 274개의 파일을 참조하는데, **모든 경로가 상대 경로(Relative Path)로 하드코딩**되어 있습니다.

* **장점:** 디렉토리 내부의 위치 관계만 지키면 경로를 단 한 글자도 수정하지 않고 통째로 복사하거나 이동시킬 수 있습니다.
* **단점:** 폴더명을 깔끔하게 정리하려 할 경우 274개의 참조 경로를 모두 수동으로 갱신해야 하며, 하나라도 누락되면 해당 집기가 텍스처를 잃고 회색으로 렌더링됩니다.

이러한 의존성 깨짐을 방지하기 위해 `scene/` 디렉토리를 원본 저장소의 루트처럼 취급하여 하위 구조를 원본 그대로 보존했습니다.

이는 개별 상품 파일(`products/`)에도 동일하게 적용됩니다. 각 상품의 USD 파일 역시 색상 텍스처를 자기 폴더 안의 상대 경로(`./textures/albedo.png`)로 탐색하므로, 개별 상품 폴더 하나만 떼어 다른 곳으로 복사하더라도 텍스처가 온전히 유지됩니다.

## GUI 화면으로 시뮬레이터 실행하기

제공된 실행 스크립트를 사용하면 호스트의 X11 디스플레이 설정을 연동하여 도커 컨테이너를 띄우고, 시뮬레이터 화면을 직접 확인할 수 있습니다.

```bash
./run/run_gui.sh
```

* 이 스크립트를 실행하면 **매장 기본 씬**(`scripts/basic_convstore.py`)이 자동으로 열립니다. 편의점 매장 전체를 배경으로 로봇이 대기하고 있는 상태를 볼 수 있습니다. (로봇을 실제로 제어하고 움직이는 작업은 참가자의 코드 영역입니다.)
* **참고:** Isaac Sim 렌더링 창이 초기화되어 뜨기까지 약 30~60초가 소요되며, 기동 중 터미널에 다수의 경고(Warning) 로그가 출력될 수 있으나 이는 정상적인 구동 과정입니다.

### 다른 씬(Scene)을 GUI로 확인하기

렌더링 창을 닫더라도 도커 컨테이너는 백그라운드에서 계속 실행된 상태를 유지합니다. 특정 과제의 씬을 화면으로 보려면, 컨테이너 내부에 접속하여 실행 명령어에서 `--headless` 옵션을 **제외하고** 스크립트를 실행하면 됩니다.

```bash
docker exec -it challenge_env bash

# 예시: 과제 B 데모 씬을 GUI 화면으로 구동
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_b_demo.py --seed 1000
```

### 🛠️ 트러블슈팅: 화면(GUI 창)이 뜨지 않을 때

실행 후에도 시뮬레이터 창이 나타나지 않는다면, 다음 순서대로 디스플레이 환경 설정을 점검해 보세요.

1. **디스플레이 환경 변수 확인:** 컨테이너 내부 터미널에서 `echo $DISPLAY` 명령어를 입력했을 때, 출력값이 비어있지 않고 정상적으로 할당되어 있는지 확인합니다.
2. **호스트 서버 권한 인가:** 호스트(Host) PC 터미널에서 `xhost +local:root` 명령어를 실행하여 도커 컨테이너의 X11 화면 접근 권한을 허용했는지 확인합니다.
3. **Wayland 사용 환경 점검:** 호스트 OS의 디스플레이 서버로 Wayland를 사용 중인 경우, XWayland 호환성 레이어가 정상적으로 동작하고 있는지 확인이 필요합니다.

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
