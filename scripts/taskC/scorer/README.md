# Task-C 채점기

`../README.md` 의 평가 기준을 코드로 옮긴 것이다. **시뮬 루프 안에서 매 스텝 판정**한다.
채점기는 로봇을 조작하지 않는다 — 관측만 한다.

```
geometry.py       해석적 최근접점(원통/박스) · AABB · 띠 교차
taskc_scorer.py   5개 항목 판정 + 중지 조건 + 리포트
selftest.py       시뮬 없이 도는 검증 (29개 검사)
```

의존성은 **numpy 하나**다. Isaac 에 묶여 있지 않아 단독으로 돌릴 수 있다.

---

## 1. 검증부터

```bash
python selftest.py
```

```
[1] 기하        원통 옆면/캡/테두리/내부 · 박스 면/꼭짓점 · 회전 AABB · 띠 걸침
[2] 시나리오    집기 -> 들기 -> 지향 -> 판독 -> 배치 = 17.0점, 중지 조건 ③
[3] 규정 준수   타이머 초기화 · 인식 전 배치 미인정 · 15cm 밖 불인정
                미배선 UNAVAILABLE · 전부 낙하 중지 · 리셋

전부 통과 — 29개 검사
```

---

## 2. 배선

관측은 전부 **콜백**으로 받는다. 시뮬 구현에 묶이지 않게 하기 위함이다.

```python
from taskc_scorer import ScoreConfig, TaskCScorer

products = [dict(
    slug="cocacola_zero",
    shape="cylinder",                     # 또는 "box"
    radius=0.033, half_height=0.0615,     # cylinder
    # half_extents=(0.05, 0.03, 0.02),    # box 일 때
    axis_local=(0, 0, 1),
    expected_code="8804409121470",
    get_pose=lambda: (pos_xyz, quat_wxyz),
    get_lin_vel=lambda: vel_xyz,
), ...]

scorer = TaskCScorer(
    products, ScoreConfig(),
    table_z=measured_table_z,             # 씬을 세운 뒤 **재서** 넣는다
    band_rect=measured_band_rect,         # 마찬가지 (x0, x1, y0, y1)
    beam_origin_fn=lambda: beam_origin_xyz,
    grasp_fn=lambda slug: bool,           # 쥔 상태인가
    gripper_load_fn=lambda slug: load_Nm,      # 그리퍼 마스터 관절 부하
    gripper_pos_fn=lambda slug: q_grip_rad,    # 같은 관절 실측 위치
    q_free_close=measured_free_close_q,        # 빈손으로 닫았을 때 서는 위치 (측정)
    in_frustum_fn=lambda slug: bool,      # 스캐너 프레임에 픽셀 1개 이상
    decode_fn=lambda slug: "읽힌 문자열" or None,
)

while running:
    sim.step()
    scorer.tick(elapsed_seconds)
    if scorer.stopped:
        break

json.dump(scorer.report(), open("score.json", "w"), ensure_ascii=False, indent=1)
```

### 콜백이 지켜야 할 것

| 콜백 | 반드시 | 이유 |
|---|---|---|
| `gripper_load_fn` | 그 상품을 쥔 **손의 마스터 관절** 부하를 반환 | 액추에이터가 하나라 이 값 하나로 족하다 |
| `q_free_close` | **빈손 닫힘을 실제로 재서** 넣을 것 | 안 넣으면 헛집기를 못 거른다 (리포트에 경고가 남는다) |
| `decode_fn` | 기하 게이트를 넘긴 프레임에서만 렌더·디코드 | 평가안 규정. 못 넘긴 프레임은 렌더 자체를 하지 않는다 |
| `decode_fn` | **스캐너 카메라** 이미지를 쓸 것 | 실물 스캐너와 같은 시점이어야 한다 |
| `table_z` `band_rect` | **씬을 세운 뒤 측정** | 상수로 박으면 안 된다. 상판은 놓이면 가라앉는다 |

채점기는 `decode_fn` 을 **거리 조건이 성립한 프레임에서만** 부른다. 렌더 비용을 아끼는 최적화가 아니라
**채점 조건 그 자체**다 — 느슨하게 잡으면 15cm 밖에서 읽은 것이 통과한다.

---

## 3. Sub 1-1 은 접촉 센서를 쓰지 않는다 ★

그리퍼는 **액추에이터가 하나**다(`gripper_master_l` -> `gripper_l_joint1`).
V홈에 물리든 팁에 물리든 **그 모터의 부하 하나로 드러난다.** 그래서 접촉 센서를 붙이지 않는다.

```
부하 = clip(stiffness x (명령 - 실측), ±effort_limit)   [N·m]
FFW_SG2 좌측: stiffness 300.0, effort_limit 30.0, velocity_limit 2.2
```

### 판정

```
① 부하 >= grip_load_min_nm            모터가 실제로 밀고 있는가
② (자유 닫힘 q) - (실측 q) >= 여유      자유 닫힘보다 덜 닫혔는가 = 사이에 뭔가 있다
   -> 둘 다 0.3초 연속
```

**②가 헛집기를 거른다.** 빈손으로 닫아도 관절 한계에 부딪히면 부하가 붙는 기구라면
①만으로는 허공을 쥔 것이 통과한다. `q_free_close` 를 **재서** 넣으면 그 구멍이 막힌다.

`q_free_close` 를 안 넣으면 ①만으로 판정하고, 리포트 `warnings` 에 그 사실을 남긴다.
조용히 넘어가지 않는다.

### 실측 근거 (에피소드 8건)

`actions.npy`(명령)와 `joints.npy`(실측)의 `gripper_l_joint1`(state 인덱스 7)에서 뽑았다.

| 상태 | 부하 | 정체 q |
|---|---|---|
| 열림·대기 | 약 **0 N·m** (명령 0, 실측 0) | — |
| 파지 중 (lift ~ sweep ~ ret) | **30 N·m 포화** | — |

| 상품 | 정체 q | 명령 | 부하 |
|---|---|---|---|
| `chilsung_cider` | 0.976 | 1.10 | 30 (포화) |
| `cocacola_zero` | 1.028 | 1.10 | 30 |
| `pringles_original_small` | 0.790 | 0.98 | 30 |
| `pringles_sourcream_small` | 0.831 | 1.03 | 30 |
| `yegam_original` | 1.019 | 1.10 | 30 |
| `lotte_sand` | 1.047 | 1.10 | 30 |
| `samyang_buldak_cup` | 0.946 | 1.05 | 30 |
| `ottogi_cupnoodle_buldak` | 0.859 | 1.10 | 30 |

정체 q 는 **0.790 ~ 1.047**. 기본 임계 `grip_load_min_nm=5.0` 은 열림(0)과 파지(30) 사이에
넉넉히 있고, `grip_stall_margin_rad=0.02` 는 가장 얇게 물린 롯데샌드(자유 닫힘 1.10 가정 시 여유 0.053)도 통과한다.

`selftest.py` 가 이 8개 실측값을 그대로 넣어 전부 통과하는지 검사한다.

> **아직 재지 않은 것**: `q_free_close`(빈손 닫힘). 위 표의 여유는 자유 닫힘을 1.10 으로 **가정**한 값이다.
> 실제로 재서 넣어야 ②가 근거를 갖는다 — §5 참조.

---

## 4. 판정 규칙이 코드에서 어떻게 지켜지나

| 규정 | 구현 |
|---|---|
| 「한 번이라도」 성립하면 통과, 뒤에 놓쳐도 점수 유지 | `_Latch.passed` — 한 번 서면 안 내려온다 |
| 한 프레임이라도 깨지면 타이머 0 | `_Latch.update()` 의 `else: self.acc = 0.0` |
| 동일 물품 2회 처리해도 무가점 | 래치라 두 번째는 상태를 바꾸지 않는다 |
| 채점 후 재수행해도 성공 유지 | 같음 |
| 인식보다 먼저 띠 안에 놓은 것은 미인정 | `judge_release()` 가 `decode.passed` 를 먼저 본다 |
| 내려놓기는 그 순간 **한 번**만 판정 | 쥠 해제 엣지에서만 호출. 이후 굴러 나가도 유지 |
| 중심이 아니라 AABB 교차 | `aabb_xy_overlaps_rect()` |
| 판 리셋 시 전부 0 | `scorer.reset()` |
| 15cm 밖 판독 불인정 | 거리 게이트가 `decode_fn` 호출 자체를 막는다 |

### 배선 안 된 항목은 0 점이 아니다

관측이 한 번도 들어오지 않은 항목은 `UNAVAILABLE` 로 남는다.

```json
"sub1_1_grip": {"pass": "UNAVAILABLE", "pts": 0.0, "t": null}
...
"warnings": ["q_free_close 미측정 -- Sub 1-1 을 모터 부하만으로 판정했다. ..."]
```

**0 점(실패)과 미측정을 구분한다.** 조용히 틀리는 것보다 못 쟀다고 말하는 편이 낫다.

---

## 5. 리포트 형식

```json
{
 "elapsed_s": 42.5,
 "stopped": "③ 전 항목 획득",
 "config":   {"grip_force_min_n": 0.5, "aim_dist_m": 0.15, ...},
 "measured": {"table_z": 0.96, "band_rect": [0.11, 0.50, -0.01, 0.57]},
 "products": [
   {"slug": "cocacola_zero",
    "items": {"sub1_1_grip": {"pass": true, "pts": 2.0, "t": 3.51}, ...},
    "points": 17.0, "max": 17.0, "fallen": false, "notes": [...]}
 ],
 "total": 17.0, "max": 51.0
}
```

`config` 와 `measured` 를 함께 남기는 이유는, 나중에 점수만 보고 **어떤 임계로 잰 것인지**
되짚을 수 있어야 하기 때문이다.

---

## 6. 아직 없는 것 ★

솔직하게 적는다. 이 채점기를 실제 평가에 쓰려면 아래가 먼저 필요하다.

| 필요한 것 | 현재 | 비고 |
|---|---|---|
| **`q_free_close` 측정** | **안 쟀다** | 빈손으로 그리퍼를 닫아 관절이 서는 위치를 한 번 재면 된다. 로봇만 띄우고 `gripper_l_joint1` 목표를 닫힘 명령으로 준 뒤 정지했을 때의 `joint_pos` 를 읽는다. 8종 전부 같은 값이므로 **한 번만 재면 계속 쓴다.** |
| **화면 점유율의 변별력** | **구현했으나 포화** | 아래 §6-1 참조. 값은 나오지만 이 카메라에서는 사실상 항상 통과한다. |
| **상판 높이 측정** | 호출자 책임 | 씬을 세운 뒤 상판 프림의 월드 AABB 최고점을 재서 넘긴다. |
| **띠 좌표 측정** | 호출자 책임 | `reach_band_final.json` 이 아니라 씬에 실제로 그려진 띠를 재는 편이 안전하다. |
| **시도(Attempt) 관리** | 미구현 | 시도 사이에 씬을 다시 까는지, 시간이 이어지는지가 평가안에 없다 → `../README.md` §6-⑤ |


### 6-1. 화면 점유율은 배선했지만 변별하지 못한다 ★

Sub 2-1 의 「프레임의 10% 이상」 조건은 `score_from_trace.coverage()` 가 계산한다.
재생기와 **같은 카메라를 해석적으로 재현**해 대상 상품의 OBB 8꼭짓점을 투영하고,
화면과 겹치는 2D 경계상자 넓이 비율을 낸다.

```
카메라 자세   eye = b0 + bd*0.03,  target = b0 + bd*0.30      (V4-250 과 동일)
카메라 스펙   1600x1000, focal 31.43mm, horizontal_aperture 20.955mm
```

**그런데 실측값이 100% 로 포화한다.** 스캐너캠의 수평 화각이 약 37도인데 제시 순간
상품이 카메라에서 수 cm 거리라, 상품이 프레임을 완전히 넘친다.

```
sub2_1_aim  PASS  3.0점  빔까지 최소 0.030m, 화면 점유 최대 100.0%
```

→ **판독 거리 안에 들어오면 10% 기준은 자동으로 충족된다.** 이 조건이 실질적으로
   거르는 것은 "상품이 카메라 뒤에 있거나 시야 밖일 때" 뿐이다.
   점수를 준다는 판정은 맞지만, **변별하는 조건이라고 믿으면 안 된다.**

두 가지를 더 못 본다.

- **가려짐** — 그리퍼나 다른 상품에 가린 부분도 넓이에 포함된다. 실제 점유율의 **상한**이다.
- **곡면** — 원통을 상자로 근사해 투영한다. 캔·컵은 실제보다 크게 잡힌다.

픽셀 단위로 정확히 재려면 스캐너캠에 인스턴스 세그멘테이션을 켜고 대상 상품의 픽셀을
직접 세야 한다. 렌더 비용이 오르므로 지금은 하지 않는다.

### 총점을 아직 확정하지 못했다

`ScoreConfig` 기준 상품당 **17점**(2+2+3+7+3), 3개면 **51점**이다.
원본 시트의 「총 합」은 **14** 인데, 수식이 `SUM(D6:D9)` 라서 **Sub 3(3점)을 빼고 더한다.**
어느 쪽이 정본인지 확정되면 배점만 고치면 된다 — 판정 로직은 그대로다.

자세한 것은 `../README.md` §6.

---

## 7. 왜 접촉 센서를 쓰지 않기로 했나

처음 초안은 평가표 원문대로 「양쪽 손가락 그룹 합력 0.5N」을 쓰려 했다. 그러려면
`ContactSensor` 를 새로 붙이고 **상품별로 힘을 분리**해 읽어야 하는데, 이 로봇에는 그럴 필요가 없다.

**그리퍼 액추에이터가 하나**이기 때문이다. 좌우 손가락이 독립적으로 움직이지 않으므로
「양쪽이 동시에 닿았는가」를 따로 물을 수 없고, 물을 필요도 없다.
V홈에 걸리든 팁에 걸리든 **모터에 걸린 부하 하나**로 드러난다.

원문의 의도(덜덜 떨며 스친 것을 거르고, 실제로 문 것만 인정)는 그대로 살아 있다 —
「0.3초 연속, 한 프레임이라도 깨지면 타이머 0」이 그 역할을 한다.
