# Task C — 인식 및 계산

> [← 메인 README 로 돌아가기](../README.md)

다음 명령어를 통해 Task C의 초기 씬을 확인할 수 있습니다.

```bash
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_c_demo.py --seed 1000
```

### 1. 환경 주요 요소

* **매장 및 계산대:** 과제 A와 동일한 편의점 전체가 생성되며, 실제 작업은 매장 남서쪽에 위치한 **계산대** 앞에서 진행됩니다. 과제 C는 정지 상태에서 수행하며, 주행은 허용되지만 필요하지 않습니다(동봉된 시연은 모두 제자리에서 수행).
* **빨간 띠 (계산대 상판):** 상판(높이 0.9035 m) 위, 로봇 기준 전방 11~50 cm · 좌측 -1~57 cm 영역에 폭 20 mm의 빨간 테이프가 표시되어 있습니다. **모든 대상 상품은 이 띠 내부에서만 스폰됩니다.**
* **상품 3개:** 전체 대상 8종 중 시드에 의해 3개가 띠 안에 무작위 배치됩니다. **슬롯 0의 상품이 로봇이 집어야 할 목표 상품**이며 나머지 2개는 방해물(배경)입니다. 3개 모두 **QR코드 면이 로봇 기준 우측(월드 좌표 -Y)을 향하며**, 원통형(프링글스, 컵라면, 캔 등)은 세워진 상태로, 상자형(예감, 롯데샌드 등)은 눕혀진 상태로 배치됩니다. 상품 간 간격은 최소 10 cm가 보장됩니다.
* **스캐너:** 로봇의 오른손이 스캐너를 쥐는 위치에 중력의 영향을 받지 않고 떠 있습니다. 상품은 왼손으로 집어 이 스캐너에 QR코드를 인식시키는 것이 핵심이며, 시연 데모는 스캐너를 해당 위치에 배치하는 것까지만 수행합니다.
* **로봇:** 계산대를 정면으로 마주 본 상태로 대기합니다. 리프트 0.0 m, 고개 39.8° 숙임, 양팔 스토우(Stow) 자세를 유지하며 바퀴는 바닥에 밀착되어 있습니다.
* **관측 카메라:** 시각 데이터 카메라는 머리 장착 `head_cam` (672×376, ZED 좌안) 1대와 양 손목 `left_wrist_cam`, `right_wrist_cam` (424×240, D405) 2대로 과제 A·B와 유사합니다.

### 2. 상품 명명 규칙

| 구분 | 예시 | 활용 |
| --- | --- | --- |
| **코드 식별자** | `pringles_original_small` | 상품 폴더 및 USD 파일명(`<이름>_phys.usd`), `products.json` 내 Key 값, JSON 데이터 `product` 항목, `--products` 옵션 |
| **영어 이름** | `small original Pringles tube` | 로봇에 하달되는 지시문(Language Instruction), JSON 내 `label` 항목 |

과제 C의 대상 상품 8종은 다음과 같습니다.

| 코드 식별자 | 영어 이름 | 형상 분류 |
| --- | --- | --- |
| `pringles_original_small` | small original Pringles tube | 원통형 |
| `pringles_sourcream_small` | small sour cream Pringles tube | 원통형 |
| `ottogi_cupnoodle_buldak` | Ottogi Buldak cup noodle | 원통형 |
| `samyang_buldak_cup` | Buldak stir-fried noodle cup | 원통형 |
| `chilsung_cider` | Chilsung cider can | 원통형 |
| `cocacola_zero` | Coca-Cola zero can | 원통형 |
| `yegam_original` | Yegam original potato chip tube | 상자형 |
| `lotte_sand` | Lotte Sand biscuit box | 상자형 |

### 3. 환경 생성 파라미터 (`--seed`, `--products`)

생성되는 씬의 형태는 기본적으로 `--seed` 옵션 하나로 모두 결정됩니다. (상품 3종의 종류, 띠 내 배치 위치, 자세 등)

* **`--seed` (환경 시드):** 고유 장면 번호입니다. **시드 0·1·2는 평가 기준용 표본 시드**로, 주최 측 정답 궤적과 동일한 장면이 생성됩니다. 이 시드에서는 무작위 배치(딜)와 재배치를 생략하고 `scripts/taskC/samples/scene_<n>.json`에 저장된 완전히 정착된 배치 상태를 그대로 불러오므로(3초간의 물리 안정화는 동일하게 수행), 정답 궤적과 mm 단위까지 동일한 위치에 상품이 스폰됩니다.
* **`--scene-file` (장면 파일 지정):** 무작위 배치를 하지 않고 제공된 장면 JSON 파일(`--scene-json` 출력 또는 정답 표본의 `scene.json`)에 기록된 상품 자세를 그대로 로드합니다. 정답 궤적 재생 및 채점 로직 검증 시 사용합니다.
* **`--products` (상품 강제 지정):** 코드 식별자 3개를 쉼표로 연결하여 전달하면 시드가 결정하는 상품 대신 해당 상품 3개를 강제로 사용합니다. **첫 번째 식별자가 목표 상품이 됩니다.** (예: `--products cocacola_zero,lotte_sand,yegam_original`)
* *참고:* 상품은 스폰 후 3초간 물리 엔진의 영향을 받아 안정화되며, 띠 밖으로 밀려나거나, 넘어지거나, QR 방위가 3° 이상 틀어지거나, 간격이 10 cm 미만으로 좁혀지면 동일 시드 내에서 최대 50회까지 자동 재배치를 수행합니다. 출력되는 좌표는 **안정화가 끝난 후 최종 측정한 실좌표**입니다.

### 4. Headless 모드를 활용한 빠른 데이터 추출

```bash
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_c_demo.py --seed 1000 --headless --seconds 1 \
    --scene-json /workspace/user/scene_c_1000.json \
    --shot /workspace/user/shot_c_1000.png
```

* **`--scene-json`:** 상품 3개의 상세 정보(월드/로봇 기준 좌표, 자세), 빨간 띠 위치, 로봇 시작 자세, 스캐너 위치, 카메라 해상도가 저장됩니다.
* **`--shot`:** 씬 생성 직후 `head_cam` 시점을 PNG로 캡처합니다.
* **`--check`:** 렌더링 구동 없이 1초 만에 상품 8종의 USD 및 QR 타일 정보, 스캐너, 매장 USD 정상 로드 여부와 빨간 띠 기하 구조를 검증합니다. 오류 발견 시 `!`로 시작하는 경고 로그를 출력하고 강제 종료(Exit code 1)합니다.

터미널 출력 예시:

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

`task_c_demo.py`가 정지된 장면을 띄운다면, `task_c_replay.py`는 로봇이 계산대의 상품을 집어 스캐너에 비추고 다시 내려놓는 시연 과정을 보여줍니다. 2가지 묶음으로 총 11개의 시연 데이터가 제공됩니다.

| 데이터 묶음 | 내용 | 편수 | 파일 위치 |
| --- | --- | --- | --- |
| **`--set gt`** | 실제 평가 기준과 동일 형식 — **잡기 → QR 인식 → 내려놓기**를 계산대 위 **상품 3개에 대해 연속 3번** 수행하는 정답 궤적 | 3편 (`--seed 0·1·2`) | `scripts/taskC/demos_gt/` |
| **`--set single`** | 모델 학습 데이터 형식 — **잡기 → QR 인식 → 내려놓기**를 **상품 1개에 대해 1번만** 수행 | 8편 (품목별 1편) | `scripts/taskC/demos/` |

```bash
cd /workspace/cyclo_lab
${ISAACLAB_PATH}/_isaac_sim/python.sh -u \
    /workspace/challenge_scripts/task_c_replay.py --set gt --seed 0
```

과제 A·B의 재생기가 기록된 좌표 수치를 단순히 시뮬레이터에 강제로 덮어씌우는 방식이었다면, 과제 C 재생기는 **기록된 관절 제어 명령(`actions.npy`, 22채널, 30 Hz)을 동일한 주기로 로봇에 인가하여 물리 엔진 내에서 상호작용하게 합니다.** (기록 데이터에는 상품의 절대 좌표가 포함되어 있지 않기 때문입니다.) 
시작 씬과 물리 조건이 동일하므로, 상품이 물리 법칙에 따라 손에 잡혀 스캐너를 통과한 뒤 목표 구역에 놓이게 됩니다. 실제 물리 연산이 동반되므로 로봇 파지(Grasping)의 안정성도 이 뷰어를 통해 점검할 수 있습니다.

하나의 에피소드는 각 상품별로 총 8개의 국면(접근 · 파지 · 들어 올림 · 스캔 동작 2회 · 내려놓기 · 후퇴 · 복귀)으로 나뉘어 진행됩니다. 재생이 완료되면 상품별 최대 들어 올림 높이, 스캐너와의 최소 근접 거리, 최종 배치 위치(영역 내/외부 여부)를 출력하며, `--summary-json` 옵션으로 저장 가능합니다.

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

#### 동봉된 데모 데이터 11종 상세

| `--set gt --seed` | 상품 처리 순서 (슬롯 0 → 1 → 2) | 프레임 수 | 재생 시간 |
| --- | --- | --- | --- |
| **0** | 오뚜기 컵누들 불닭 → 예감 오리지널 → 삼양 불닭 컵 | 9,242 | 308초 |
| **1** | 삼양 불닭 컵 → 오뚜기 컵누들 불닭 → 예감 오리지널 | 7,567 | 252초 |
| **2** | 삼양 불닭 컵 → 예감 오리지널 → 오뚜기 컵누들 불닭 | 8,236 | 275초 |

| `--set single --seed` | 처리 대상 상품 | 프레임 수 | 재생 시간 |
| --- | --- | --- | --- |
| **0** | 프링글스 오리지널 (소) (`pringles_original_small`) | 3,099 | 103초 |
| **1** | 프링글스 사워크림 (소) (`pringles_sourcream_small`) | 2,849 | 95초 |
| **2** | 오뚜기 컵누들 불닭 (`ottogi_cupnoodle_buldak`) | 1,928 | 64초 |
| **3** | 예감 오리지널 (`yegam_original`) | 1,983 | 66초 |
| **4** | 삼양 불닭 컵 (`samyang_buldak_cup`) | 2,703 | 90초 |
| **5** | 칠성사이다 캔 (`chilsung_cider`) | 2,731 | 91초 |
| **6** | 코카콜라 제로 캔 (`cocacola_zero`) | 2,097 | 70초 |
| **7** | 롯데샌드 (`lotte_sand`) | 2,268 | 76초 |

동봉된 기록은 모두 수집 파이프라인에서 성공 판정(QR 인식 1회 이상, 띠 안 배치)을 받은 것입니다. 이 재생기로 상품이 들려 스캐너를 거쳐 띠 안 제자리로 돌아오는 것까지 재현을 확인한 데이터는 `gt` 시드 0과 `single` 시드 6(코카콜라)이며, `single` 시드 5(칠성사이다)는 재생 시 파지가 재현되지 않아 다른 기록으로 교체할 예정입니다.

#### 재생 제어 옵션

| 옵션 | 설명 |
| --- | --- |
| `--set gt` 또는 `--set single` | 재생할 데이터 세트 선택 (기본값: gt) |
| `--seed N` | 해당 세트 내 에피소드 번호 지정 (gt: 0~2, single: 0~7 / 기본값: 0) |
| `--list` | 저장된 에피소드 목록만 출력하고 종료 (Isaac Sim 구동 안 함) |
| `--episode DIR` | 데이터 세트 대신 재생할 기록 폴더 경로를 직접 지정합니다. |
| `--substeps N` | 1프레임을 몇 단계의 물리 연산 스텝으로 보간할지 설정 (기본값: 4 = 기록과 동일 속도) |
| `--no-interp` | 인접 프레임 간의 제어 명령을 선형 보간(Linear interpolation)하지 않습니다. |
| `--frames N` | 지정한 N 프레임까지만 재생합니다 (0일 경우 전체 재생). |
| `--start-hold S` | 재생 전 첫 프레임 자세로 S초 동안 대기합니다 (기본값: 1.0초). |
| `--summary-json FILE` | 상품별 최종 수행 결과를 지정한 JSON 파일로 저장합니다. |
| `--headless` | 렌더링 화면 없이 백그라운드에서 실행합니다. |

### 6. Task C 채점기 (Standalone)

과제 C의 평가 기준(상품 1개당 5개 항목, 총 17점: 파지 2점 · 들어 올림 2점 · 스캐너 조준 3점 · QR 인식 7점 · 띠 안 배치 3점)이 반영된 채점 코드가 `scripts/taskC/scorer/` 디렉토리에 제공됩니다. 시뮬레이션 루프 내에서 매 스텝 관측치를 받아 판정하며(`taskc_scorer.py`), Isaac Sim 없이 Numpy만으로 동작하는 자체 검증 모듈이 포함되어 있습니다.

```bash
python3 scripts/taskC/scorer/selftest.py      # 기하학적 수치, 시나리오, 규정 준수 등 35개 테스트 수행
```
평가 기준 원문과 미확정 항목(제한 시간, 총점 표기)은 `scripts/taskC/scorer/EVALUATION_DRAFT.md`, 채점기 연동 방법은 `scripts/taskC/scorer/README.md`를 참고하시기 바랍니다.

*현재 재생 중 실시간 채점(`[점수]` 로그 출력) 기능은 준비 중이며, 채점 기준표는 추후 변동될 수 있습니다.*

### 7. 좌표계 정보
바닥면이 Z = 0이며 매장 좌표계는 과제 A와 동일합니다. 계산대 중심축은 (-4.00, -4.22)에 위치하며, 로봇은 그 앞인 (-3.45, -4.27)에서 +Y 방향을 바라봅니다. 씬 JSON 내부의 상품 좌표는 월드 절대 좌표(`pos`)와 로봇 기준 상대 좌표(`pos_robot`: x축 전방, y축 좌측)가 모두 제공됩니다.
