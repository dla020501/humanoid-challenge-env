# Copyright 2026.
#
# 과제 C 장면의 고정 기하. 계산대가 어디 있고, 로봇이 어디 서며, 상품이 놓이는 빨간 띠가
# 어디이고, 스캐너와 카메라가 어떻게 달리는지.
#
# 값의 출처는 옆 주석에 적었다. 대회 환경 저장소의 `taskC/kit_config.py`(계산대·로봇·띠·
# 스캐너)와 `fixture_kit/make_store.py`(구워진 매장 안 계산대 자리), 그리고 과제 A/B 데모의
# 카메라 정의다. 숫자를 여기 옮겨 적는 이유는 과제 A 와 같다 -- `scripts/` 는 마운트라
# `git pull` 만으로 갱신되고, 참가자가 장면이 어떻게 정해지는지 GitHub 에서 바로 읽을 수 있다.
#
# 두 좌표계가 나온다.
#   세계(store)  구워진 매장 USD 의 좌표. 바닥이 z = 0, 과제 A 와 같다.
#   로봇(robot)  로봇 베이스가 원점이고 +x 가 로봇 앞(계산대 쪽), +y 가 로봇 왼쪽이다.
#                띠와 배치 규칙은 이 좌표로 적혀 있다 -- 수집 파이프라인이 그렇게 쓴다.
#
# isaaclab 을 쓰지 않는 순수 파이썬이다.

import math as _math
import os

# --------------------------------------------------------------------------- 계산대
#
# 구워진 매장(`store/scene/fixture_kit/out/store_scene.usd`) 안의 계산대. make_store.py 가
# `("cash_table", (-4.00, -4.22), FACE_PLUS_Y)` 로 놓는다. 수집 파이프라인의 kit_config 는
# convstore_store 판 계산대 (-4.00, -3.50) 를 기준으로 하고, 구워진 매장을 쓸 때는 매장을
# +Y 0.72 m 옮겨 두 계산대를 겹쳤다(V4-235). 여기서는 반대로 매장을 그대로 두고 로봇과
# 띠를 -0.72 m 옮긴다 -- 매장 좌표가 과제 A 와 같아지도록.
COUNTER_CENTRE_WORLD = (-4.00, -4.22)
COUNTER_TOP_Z = 0.9035                    # kit_config.COUNTER_TOP_Z (= convstore_store)
COUNTER_SIZE_XY = (3.2329, 1.80)          # store manifest, cash_table.size
COUNTER_FACE = "+x"                       # 로봇 좌표에서 계산대는 로봇 앞(+x)에 있다

# 매장에는 계산대 위에 정적 스캐너 소품이 하나 놓여 있다(make_store.py `("scanner",
# (-3.40, -3.92), ...)`). 과제 C 는 스캐너를 로봇이 드는 강체로 따로 스폰하므로 그 소품은
# 데모가 비활성화한다 -- 둘이면 장면에 스캐너가 두 개가 된다.
STORE_STATIC_SCANNER_XY = (-3.40, -3.92)

# --------------------------------------------------------------------------- 로봇
#
# kit_config: ROBOT_BASE_WORLD = (-3.50 + BASE_RIGHT 0.05, -3.70 + BASE_FORWARD 0.15) 를
# convstore 계산대 기준으로 적은 값. 위의 0.72 m 만큼 -Y 로 옮긴다.
_SHIFT_Y = COUNTER_CENTRE_WORLD[1] - (-3.50)          # = -0.72

# 계산대에서 뒤로 물리는 양. 학습 데이터의 머리캠과 우리 머리캠에 찍힌 **띠 네 모서리**를
# 맞춰 잰 값이다. 띠 사각형은 로봇 좌표가 정확히 알려져 있고(BAND, 상판 z 0.9035) 화각도
# 같으므로, 그 네 점의 화소 위치에서 카메라 자세를 역산할 수 있다. 실측:
#
#   보정 없음        네 모서리 잔차 12.48 px
#   각도만 맞춤      잔차  2.64 px  (피치 -1.72 도가 필요)
#   위치만 맞춤      잔차  0.77 px  (앞뒤 -23.1 mm)     <- 이쪽이 3 배 이상 잘 맞는다
#
# 즉 어긋남은 카메라 각도가 아니라 로봇이 계산대에 23 mm 가까이 서 있던 것이다. 로봇 +x 가
# 세계 +y 이므로(요 90 도) y 를 그만큼 줄인다. 0 을 주면 보정이 꺼진다.
# 로봇을 계산대에서 뒤로 물리는 양. **0 이 맞다.**
#
# 한때 23.1 mm 를 넣었다. 머리캠 전체 평균차가 17.00 -> 15.29 로 좋아졌기 때문인데, 그 지표는
# 화면 오른쪽 절반을 차지하는 팔·스캐너에 지배당하는 값이었다(그때는 스캐너 용접이 없어 자세가
# 크게 달랐다). 계산대·로봇·상품·띠 네 대상의 **모든 쌍 거리**로 다시 재니 어긋난 것은 계산대가
# 낀 다섯 쌍뿐이었고(-6 ~ -21 mm), 그 값이 정확히 이 이동에서 나왔다:
#
#   로봇-띠 / 로봇-상품 / 띠-상품 / 상품끼리   0.0 mm      (전부 씬 JSON 로봇 좌표)
#   로봇-계산대 +2.6 · 계산대-띠 -15.5 · 계산대-상품 -6.4 ~ -21.1 mm
#
# 계산대는 세계에 고정이고 나머지 셋은 로봇을 따라가므로, 로봇을 옮기면 그 관계만 깨진다.
# 로봇을 계산대에서 이만큼 뒤로 물린다.
#
# 로봇이 상수가 가정하는 자리보다 **19 mm 앞**에 서 있다. 근거 셋:
#
#   섀시 절대 위치   `world` 링크 y -4.2511 vs 상수 -4.2700  ->  +18.9 mm 앞
#   머리캠 화면      계산대 먼 모서리가 GT 59.89 행, dev 65.89 행 -> 6.00 px
#                    (0.7 초 이후 9 초까지 표준편차 0.194 px 로 상수. 정착은 1.0 초에 끝난다)
#   전후 환산        6.00 px / 349.3 px/m = 17.2 mm
#
# 높이가 아니라 전후다. 높이로 환산하면 19.9 mm 인데 그쪽엔 근거가 없다 -- `WHEEL_RADIUS`
# 0.0864 는 실제 바퀴 0.0865 와 0.1 mm 차이뿐이고 리프트 침하도 -2.6 mm 뿐이다.
#
# **띠·상품에는 역보정을 넣지 않는다.** 둘 다 로봇 좌표로 놓이므로 로봇과 함께 움직이고,
# 그래야 손↔상품 관계가 보존된다. 상품만 제자리에 두면 파지가 무너진다(예전 실측:
# 상품을 옮겼더니 들림 212.7 -> 1.7 mm). 실제로 20 mm 실험에서 컵의 화면 위치는
# +8.47 -> +8.51 px 로 불변이었고 계산대 모서리만 +7 -> 0 px 로 맞았다.
BASE_BACK = float(os.environ.get("TASKC_BASE_BACK", "0.019"))
ROBOT_BASE_WORLD = (-3.45, -3.55 + _SHIFT_Y - BASE_BACK, 0.0)
ROBOT_YAW = _math.pi / 2.0                # 세계 +Y 를 본다 = 계산대 위로
LIFT_JOINT_POS = 0.0                      # kit_config.LIFT_JOINT_POS
HEAD_PITCH = 0.6951                       # V4-139: 60 도를 요청하지만 관절 한계 0.6951 rad(39.8 도)
HEAD_YAW = 0.0
# kit_config.STOW_ARM_POS -- 오른팔 값. 왼팔은 joint2·joint3 의 부호를 뒤집는다
# (kit_config.stow_joint_pos 실측: 두 팔의 그 두 관절 가동범위가 거울상이다).
STOW_ARM_R = (1.2000, -0.4500, -0.0632, -2.5870, 0.0, 0.0, 0.0)
STOW_ARM_L = (1.2000, 0.4500, 0.0632, -2.5870, 0.0, 0.0, 0.0)
WHEEL_RADIUS = 0.0864                     # 과제 A/B 데모와 같은 값

# 시작 자세. 학습 데이터(HF `taskC/`, 960 편)의 **첫 프레임 그대로**다. 그 데이터의 f0 은
# `observation.state` 와 `action` 이 완전히 같고 앞 여섯 프레임의 변화가 0 이다 -- 즉 로봇이
# 명령값에 정확히 도달한 채 정지해 있는 상태에서 에피소드가 시작한다. 정책은 이 자세를 t=0 의
# 관측으로 배웠으므로 평가 환경도 같은 자세에서 출발해야 한다.
#
#   왼팔      STOW_ARM_L 과 정확히 같다 (1.20000, 0.45000, 0.06320, -2.58700, 0, 0, 0)
#   오른팔    스캐너를 든 홀드 자세 (아래)
#   오른 그리퍼 0.90 (스캐너를 쥔 상태), 왼 그리퍼 0
#   머리 0.69510 / 0,  리프트 0
#
# 기록의 첫 프레임(`initial_state.json` 의 `robot_joint_pose`)은 밀의 **실측**이라 명령값과
# 최대 4.5 mrad 다르다. 학습 데이터가 기대하는 것은 명령값 쪽이다.
HOLD_ARM_R = (2.25102, -1.83197, -1.17518, -1.88526, -0.85715, -0.88668, 0.15830)
GRIP_R_START = 0.90000
GRIP_L_START = 0.0


def start_joint_pos() -> dict:
    """{관절 이름: rad}. 학습 데이터 첫 프레임과 같은 시작 자세."""
    out = {}
    for i, v in enumerate(STOW_ARM_L, 1):
        out[f"arm_l_joint{i}"] = float(v)
    for i, v in enumerate(HOLD_ARM_R, 1):
        out[f"arm_r_joint{i}"] = float(v)
    out["gripper_l_joint1"] = float(GRIP_L_START)
    out["gripper_r_joint1"] = float(GRIP_R_START)
    out["head_joint1"] = float(HEAD_PITCH)
    out["head_joint2"] = float(HEAD_YAW)
    out["lift_joint"] = float(LIFT_JOINT_POS)
    return out

# --------------------------------------------------------------------------- 빨간 띠
#
# 상품이 놓이는 사각형 (로봇 좌표). `.urdf_export/reach_band_final.json` 의 x0/x1/y0/y1.
# 테이프 폭 20 mm 는 띠 안쪽에서 뺀다 -- 상품이 테이프에 닿아서도 안 된다.
BAND = {"x0": 0.1101, "x1": 0.4999, "y0": -0.01, "y1": 0.57}
TAPE_W = 0.02
TAPE_T = 0.005                            # kit_config.TAPE_T -- 테이프 두께 5 mm
TAPE_COLOR = (0.80, 0.03, 0.03)           # qr_scene 이 그리는 빨간 띠 색

# 배치 규칙 상수 (qr_scene.deal)
STOW_GRIP_XY = (0.19, 0.30)               # QR-35: 스토우 자세의 왼손 그리퍼가 띠 위에 떠 있는 자리
STOW_GRIP_CLEAR = 0.14                    # 그 아래 반경 0.14 m 에는 상품을 놓지 않는다
MIN_GAP = 0.10                            # QR-11: 상품 표면-표면 >= 10 cm
QR_TARGET_YAW_DEG = -90.0                 # kit_config.BARCODE_TARGET_YAW_DEG: QR 면이 세계 -Y(정 오른쪽)
QR_AZ_TOL_DEG = 3.0                       # QR-62: 정착 후 허용 오차 +-3 도
MAX_REDEAL = 50

# --------------------------------------------------------------------------- 스캐너
#
# 에피소드 시작 순간 스캐너는 오른손이 드는 자리에 떠 있다(중력 없음). 수집 재생기가 같은
# 자세로 스폰한다: kit_config.SCANNER_HOLD_POS / SCANNER_HOLD_QUAT (로봇 좌표).
# 스캐너를 든 자세. 09-07 확정 빌드(`scripts_same2a`, 슬롯0 들림 206.7 mm)가 쓰던 값이다.
# `kit_config.SCANNER_HOLD_POS` 의 승인값 (0.330, -0.1578, 1.161) 을 그대로 쓰면 정착이 끝난
# 오른손에서 스캐너까지가 **207 mm** 로 잡힌다. 확정 빌드의 실측 파지는 **167.74 mm** 이고,
# 그 값은 아래 자세에서 나온다. 그 차이만큼 스캐너가 손에서 떠 있어 오른손 자세가 14 mm,
# `arm_r_joint1` 이 25 mrad 어긋났다.
# `.urdf_export/taskC_beam.json` 의 `scanner_hold_pos` 에 x 를 +17.9 mm 더한 값이다.
#
# 그 파일은 스캐너 자리와 **손목 자리(`hold_tool_pos`)를 같은 좌표계로** 함께 적어 두는데,
# 둘의 차이가 v5 가 실제로 만든 손-스캐너 관계다:
#     v5   손목 -> 스캐너   (+0.0759, +0.1574, -0.0266)   176.71 mm
#     dev  link7-> 스캐너   (+0.0580, +0.1577, -0.0251)   169.88 mm
#     차                    (-17.9,   +0.3,    +1.5) mm      <- x 만 어긋난다
#
# 우손목캠으로 독립 검증한 값도 같다. 초록 창의 화면 위치를 GT(f33) 와 맞추는 이동량을
# 축별 8 mm 흔들기로 잰 야코비안에서 풀면 dx +15.9 ~ +16.0 mm 가 나오고(y·z 는 0.5 mm 이내),
# 실제로 넣어 재면 +17.9 mm 가 최선이다:
#     보정 전  LED 가 GT 에서 46.44 px,  몸통 실루엣 IoU 0.667
#     +16.0    LED  7.01 px,  IoU 0.855
#     +17.9    LED  5.22 px,  IoU 0.883   <- 위치·실루엣 모두 최선
# 슬롯0 들림 219.2 mm, 들어올림 O 는 그대로다.
SCANNER_HOLD_POS = (0.3095930, -0.1794305, 1.1104370)
SCANNER_HOLD_QUAT = (0.6890703, 0.6890704, -0.1586886, -0.1586886)

# 스캐너 몸통 기준 빔이 나오는 자리 (`kit_config.py:1801`). 빔 방향은 스캐너 로컬 -Z 다.
SCANNER_EMIT_LOCAL = (0.000080, 0.062708, -0.038814)
SCANNER_SIZE = (0.0674, 0.1607, 0.0872)

# --------------------------------------------------------------------------- 카메라
#
# 채점이 정책에게 보내는 관측 셋. 머리는 과제 A 데모의 값(zed/cam_head), 손목은 과제 B 데모의
# 값(424x240) 그대로다. prim 경로는 로봇 prim 아래 상대 경로.
# 초점거리·클리핑은 학습 데이터를 만든 수집 파이프라인의 값 그대로다 (qr_sweep_replay.py
# 469~480 `rec_head`/`rec_wl`/`rec_wr`). 그 판은 focal 과 clipping 만 주고 나머지는
# IsaacLab 기본값(조리개 20.955, 초점거리 400)에 맡기므로 여기서도 같은 수를 적는다.
#   머리  focal 10.5  clip (0.05, 20.0)   HFOV 약 90 도 (실기급 광각)
#   손목  focal 11.0  clip (0.03, 10.0)   HFOV 약 87 도
# 손목이 18.0 이면 화각이 60 도라 기록과 다른 그림이 나온다.
def _q_rpy(r_, p_, y_):
    """URDF 의 rpy(고정축 XYZ, R = Rz(y)Ry(p)Rx(r))를 쿼터니언 (w, x, y, z) 로."""
    cr, sr = _math.cos(r_ / 2), _math.sin(r_ / 2)
    cp, sp = _math.cos(p_ / 2), _math.sin(p_ / 2)
    cy, sy = _math.cos(y_ / 2), _math.sin(y_ / 2)
    return (cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy)


# 실기 URDF(ai_worker ffw_sg2_follower.urdf) 장착 상수. 수집 파이프라인
# (qr_sweep_replay.py 1462~1480)의 값을 그대로 옮긴 것이다.
#
#   ZED Mini 왼눈 : head_link2 + (0.0238122, -0.00651797+0.0315, -0.0242094+0.01325)
#                   여기에 사용자 지시로 카메라를 30 도 더 숙인다(관절 한계 보완).
#   D405         : link7 + rpy(-pi/2, 1.66678943569, 0), xyz(0.108236, -0.021, -0.062552)
#                   -> camera_link 로 다시 (0.01085, 0.009, 0.021) (스크류 프레임 기준)
#
# 자세 합성은 `wq = lq * rot`, 위치는 `lp + lq*off0 + wq*off1` 이다. off1 만 회전된
# 프레임에서 더한다 -- 순서를 바꾸면 손목캠이 수 cm 어긋난다.
# 카메라 자체의 추가 하향. v5 `_ZED_Q = _q_rpy(0, radians(30), 0)` 과 같은 30 도다.
# `head_joint1` 이 URDF 한계 +0.6951 rad(39.83 도)에 이미 붙어 더 못 숙이므로 카메라 쪽에
# 각을 더한 것이다(V4-139: "60도는 관절 한계 밖이라 한계값 39.8도가 최대").
#
# **이 값은 맞다.** 계산대 위 띠의 좌우 변은 세계에서 평행이라 영상에서 만나는 점의 행이
# 지평선이고, 거기서 카메라 하향 피치가 기하로 나온다(추정이 아니다). 실측:
#
#     GT  f54   좌변 x=-0.3032y+114.5  우변 x=+0.0208y+348.3  -> 소실점 -721.4 행 -> 69.68 도
#     dev f21   좌변 x=-0.3020y+115.0  우변 x=+0.0197y+348.2  -> 소실점 -724.8 행 -> 69.75 도
#     계산      head_joint1 39.83 + 장착 30.0 = 69.83 도      (직선 적합 잔차 0.28 px)
#
# 차이가 0.07 도다. 한때 계산대 먼 모서리가 GT 60 행 대 dev 67 행인 것을 보고 30.90 도를
# 넣어 봤으나(그 한 선은 맞았다), 배경의 두 번째 선은 3.03 px 남고 두 선 간격이 GT 보다
# 2.5~4 px 큰 것이 어느 각도에서도 안 사라졌다. 회전으로는 못 없애는 성분이 있다는 뜻이고,
# 위 소실점 실측이 그것을 확정했다 -- **카메라는 맞고 매장(계산대) 쪽이 어긋나 있다.**
# 띠는 dev 가 세계 좌표로 직접 그리므로 GT 와 같은 자리에 맺히고, 계산대는 매장 USD 에서 온다.
HEAD_CAM_PITCH = _math.radians(float(os.environ.get("TASKC_HEAD_CAM_PITCH_DEG", "30.0")))
_ZED_OFF = (0.0238122, 0.0249820, -0.0109594)
_ZED_ROT = _q_rpy(0.0, HEAD_CAM_PITCH, 0.0)
_W_ROT = _q_rpy(-_math.pi / 2.0, 1.66678943569, 0.0)
_W_OFF0 = (0.108236, -0.021, -0.062552)
_W_OFF1 = (0.01085, 0.009, 0.021)

# 초점거리·클리핑도 수집 판(rec_head/rec_wl/rec_wr, 같은 파일 469~480)의 값이다. 그 판은
# focal 과 clipping 만 주고 나머지는 IsaacLab 기본값(조리개 20.955, 초점거리 400)에
# 맡기므로 여기서도 같은 수를 적는다.
#   머리 focal 10.5 clip (0.05, 20.0) HFOV 약 90 도 · 손목 focal 11.0 clip (0.03, 10.0) 약 87 도
#
# `rot180` 은 **저장하는 그림**을 180 도 돌린다는 뜻이다(v5-10, 같은 파일 1529 줄).
# 카메라 자세에는 롤이 없다 -- 손목 기록만 뒤집혀 저장된다.
CAMERAS = {
    "head_cam": dict(
        prim="HeadCam", body="head_link2", w=672, h=376,
        focal=10.5, focus=400.0, aperture=20.955, clip=(0.05, 20.0),
        off0=_ZED_OFF, rot=_ZED_ROT, off1=(0.0, 0.0, 0.0), rot180=False),
    "left_wrist_cam": dict(
        prim="WristCamL", body="arm_l_link7", w=424, h=240,
        focal=11.0, focus=400.0, aperture=20.955, clip=(0.03, 10.0),
        off0=_W_OFF0, rot=_W_ROT, off1=_W_OFF1, rot180=True),
    "right_wrist_cam": dict(
        prim="WristCamR", body="arm_r_link7", w=424, h=240,
        focal=11.0, focus=400.0, aperture=20.955, clip=(0.03, 10.0),
        off0=_W_OFF0, rot=_W_ROT, off1=_W_OFF1, rot180=True),
}


def band_inner():
    """테이프 폭만큼 안쪽으로 들어온 (x0, x1, y0, y1) -- 상품이 있어도 되는 영역(로봇 좌표)."""
    # 띠·상품·팔이 모두 로봇 상대다(기록은 관절값뿐, 씬 JSON 은 로봇 좌표). 로봇을
    # `BASE_BACK` 만큼 옮겨도 셋이 함께 움직이므로 여기에는 그 보정을 넣지 않는다.
    # 넣으면 팔만 원래 자리를 짚어 손이 그만큼 못 미친다(실측: 들림 212.7 -> 1.7 mm).
    return (BAND["x0"] + TAPE_W, BAND["x1"] - TAPE_W, BAND["y0"] + TAPE_W, BAND["y1"] - TAPE_W)


def stow_joint_pos() -> dict:
    """{관절 이름: rad}. kit_config.stow_joint_pos() 와 같은 값."""
    out = {}
    for i, (r, l) in enumerate(zip(STOW_ARM_R, STOW_ARM_L), 1):
        out[f"arm_r_joint{i}"] = float(r)
        out[f"arm_l_joint{i}"] = float(l)
    return out


def apply_rot180(cam_name, img):
    """`CAMERAS[cam_name]["rot180"]` 이 참이면 그림을 180 도 돌린다 (v5-10).

    v5 는 저장 직전에 손목캠만 돌린다 (`qr_sweep_replay.py:1529`,
    `TASKC_WRIST_ROT180` 기본 1). 기록이 그렇게 남았으므로 관측을 만드는 쪽은
    반드시 같은 처리를 해야 한다. 돌리지 않은 그림을 GT 와 대면 평균차가
    109.4 로 나오고, 돌리면 21.8 이 된다 (2026-09-09 우손목 f0 실측).
    """
    if not CAMERAS[cam_name].get("rot180"):
        return img
    return img[::-1, ::-1]


# 띠·상품을 로봇 이동에서 떼어 놓는 양.
#
# 띠와 상품은 로봇 좌표로 적혀 있어 `BASE_BACK` 으로 로봇을 물리면 함께 끌려간다. 그런데
# 그 둘은 **계산대에 놓인 것**이지 로봇에 붙은 것이 아니다. 실측: `BASE_BACK=0` 에서 띠의
# 세계 사각형이 GT 와 완전히 일치했고(y[-4.160,-3.770]), 19 mm 를 넣으니 y[-4.179,-3.789]
# 로 그만큼 어긋났다. 화면으로도 띠가 GT 보다 8~11 px 로봇 쪽에 붙는다.
#
# 그래서 그만큼 앞으로 되돌린다. 기본은 `BASE_BACK` 과 같은 값이라 띠·상품이 로봇 이동에
# 영향받지 않는다. 0 을 주면 종전대로 함께 끌려간다.
#
# **띠에만 쓴다.** 상품·스캐너는 `robot_to_world` 로 기록 자리에 그대로 둔다 -- 팔 궤적이
# 그 자리를 전제로 계획된 것이라 옮기면 턱이 중심을 못 물고 물체가 옆으로 튄다(실측: 19 mm
# 옮기니 y 로 24 mm 밀려 나가고 쥐는 힘이 0.19 -> 0.047, 들림 213 -> 40 mm). 스캐너도
# 마찬가지로 파지가 y 17 mm · z 8 mm 어긋난다. 수집 파이프라인도 상품을 로봇 좌표에 그대로
# 놓으며 보정 장치가 없다(`pos=tuple(p["pos"])`).
#
# 띠는 팔이 건드리지 않으므로 안전하고, 이 값에서 세계 사각형이 GT 와 정확히 일치한다:
#
#     GT 환산            x[-4.020,-3.440]  y[-4.160,-3.770]
#     SCENE_FWD 0        x[-4.020,-3.440]  y[-4.179,-3.789]   19 mm 어긋
#     SCENE_FWD 0.019    x[-4.020,-3.440]  y[-4.160,-3.770]   일치
#
# 물리에는 영향이 없다 -- 강성 x1 판에서 0 과 0.019 의 들림이 206.8 mm 로 소수점까지 같았다.
SCENE_FWD = float(os.environ.get("TASKC_SCENE_FWD", "0.019"))


def scene_to_world(p):
    """계산대에 놓이는 것(띠·상품)의 로봇 좌표 -> 세계 좌표.

    `robot_to_world` 와 같지만 `SCENE_FWD` 만큼 로봇 앞쪽으로 되돌려, 로봇을 물려도
    계산대 기준 자리가 유지된다.
    """
    return robot_to_world((p[0] + SCENE_FWD,) + tuple(p[1:]))


def world_to_robot(p):
    """세계 (x, y[, z]) -> 로봇 좌표."""
    dx, dy = p[0] - ROBOT_BASE_WORLD[0], p[1] - ROBOT_BASE_WORLD[1]
    c, s = _math.cos(-ROBOT_YAW), _math.sin(-ROBOT_YAW)
    out = (c * dx - s * dy, s * dx + c * dy)
    return out + tuple(p[2:]) if len(p) > 2 else out


def robot_to_world(p):
    """로봇 (x, y[, z]) -> 세계 좌표."""
    c, s = _math.cos(ROBOT_YAW), _math.sin(ROBOT_YAW)
    out = (ROBOT_BASE_WORLD[0] + c * p[0] - s * p[1],
           ROBOT_BASE_WORLD[1] + s * p[0] + c * p[1])
    return out + tuple(p[2:]) if len(p) > 2 else out


def quat_mul(a, b):
    """(w, x, y, z) 곱."""
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def robot_yaw_quat():
    """로봇 좌표 -> 세계 좌표 회전 (세계 Z 축 +90 도)."""
    return (_math.cos(ROBOT_YAW / 2.0), 0.0, 0.0, _math.sin(ROBOT_YAW / 2.0))


def quat_robot_to_world(q):
    """로봇 좌표에서 적힌 자세 쿼터니언을 세계 좌표로."""
    return quat_mul(robot_yaw_quat(), q)


def quat_world_to_robot(q):
    yq = robot_yaw_quat()
    return quat_mul((yq[0], -yq[1], -yq[2], -yq[3]), q)
