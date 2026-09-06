# Copyright 2025.
#
# **씬 배치 파일이 무엇을 담는가**, 그리고 두 파일이 같은 씬인지 어떻게 대조하는가.
#
# WHY THIS FILE EXISTS
#   이 저장소에는 "장면 하나"를 적어 둔 파일이 없다.  장면은 *코드 + eatin_measured.json +
#   destinations.json + 명령줄 정수 몇 개*(seat, store_seed, shelf_seed, ...)로 암시될 뿐이고,
#   가장 완전한 기록인 hdf5 의 `scene` attr 조차 크레이트·책상·로봇의 월드 자세를 하나도
#   안 담는다 (`carry_episode.py:4498`).  그래서 남에게 "이 장면으로 채점기를 시험하세요" 라고
#   줄 수 있는 것이 없다.  이 파일이 그 형식을 정의한다.
#
# 두 가지 규칙이 형식을 결정했다
#   ① **전부 실측해서 적는다.**  코드에 있는 상수를 옮겨 적지 않는다.  앞 판에서 옮겨 적은
#      숫자 일곱 개가 틀렸고 그중 셋은 데이터가 아예 없었다.  그래서 `export_scene.py` 는
#      시뮬레이터를 띄우고 정착까지 시킨 다음 **씬에서 읽어서** 이 파일을 쓴다.
#   ② **적은 것으로 다시 세워지는지 확인한다.**  `export_scene.py --verify` 가 이 파일만 보고
#      장면을 다시 지어 재실측하고, 항목별로 대조한다.  빠진 항목이 있으면 거기서 걸린다.
#      "적었다" 와 "재현된다" 는 다르다.
#
# 순수 파이썬이다 -- Isaac 없이 읽고 대조할 수 있어야 받는 분이 쓸 수 있다.

import json
import math

SCHEMA_VERSION = 3

# 대조 허용치.  물리는 같은 GPU 에서 소수점 끝자리까지 재현된다(Task-A/CLAUDE.md 68 절)므로
# 원칙적으로 0 이어도 된다.  1e-6 을 두는 것은 JSON 왕복에서 생기는 자리 손실 때문이고,
# **대조 결과에는 실제 최대 오차를 같이 찍는다** -- 통과했다는 말보다 그 숫자가 정보다.
#
# 실측 2026-09-01: 같은 기계에서는 24 항목 전부 오차 0.000e+00 이다.  **기계를 바꾸면 로봇만
# 갈라진다.**  Blackwell 에서 만든 씬 파일을 4090 에서 되짚었더니:
#
#   로봇 루트          6.390e-03 m      그리퍼 링크 8 개   3.48~3.65e-03 m
#   로봇 관절          2.011e-02 rad (1.15 도)
#   바구니             5.9e-08 m        책상               2.4e-07 m
#   가구 / 스툴 / 목표 / 치수            0.000e+00
#
# 가르는 것이 무엇인지가 이 숫자에 그대로 있다 -- **정착이 풀이인 것만 갈라진다.**  바구니는
# 탁상 위에 그냥 놓여 있고 가구는 아예 안 움직이므로 기계를 타지 않는다.  로봇은 31 자유도
# 관절계가 2 초에 걸쳐 내려앉는 것이라 솔버의 감축 순서를 탄다.
#
# **그래서 씬 파일은 GT 를 만들 기계에서 만들어야 한다.**  `meta.gpu` 가 그것을 위해 있다.
TOL = {
    "pos_m": 1.0e-6,
    "quat": 1.0e-6,
    "joint_rad": 1.0e-6,
    "size_m": 1.0e-6,
}

# 그리퍼 링크 여덟 개.  평가표 A-1-2 / A-2-2 가 "이 여덟 개 가운데 어느 하나와든" 이라고
# 말하는 그 여덟 개다.  이름은 `Task-A/scoring/probe_pick.py:38` 과
# `scripts/tools/task_b_episode.py:600-607` 에서 왔다.
GRIP_LINKS = (
    "gripper_l_rh_p12_rn_l1", "gripper_l_rh_p12_rn_l2",
    "gripper_l_rh_p12_rn_r1", "gripper_l_rh_p12_rn_r2",
    "gripper_r_rh_p12_rn_l1", "gripper_r_rh_p12_rn_l2",
    "gripper_r_rh_p12_rn_r1", "gripper_r_rh_p12_rn_r2",
)

# USD 안에서의 프림 경로.  왼손은 `left_gripper/`, 오른손은 `right_gripper/` 밑에 있다.
GRIP_PRIM = {b: f"{'left' if '_l_' in b else 'right'}_gripper/{b}" for b in GRIP_LINKS}


def blank():
    """빈 씬 파일.  어떤 열쇠가 있는지가 곧 문서다."""
    return {
        "schema": SCHEMA_VERSION,
        # ── 어떻게 만들어진 장면인가.  다시 지으려면 이것만 있으면 된다 ──────────────────
        "meta": {
            "name": None,              # scene_1 …
            "segment": None,           # pick / carry / place -- 어느 구간용 장면인가
            "seat": None,              # 식사공간 좌석 0~11.  로봇과 바구니의 출발 자리
            "corridor": None,          # central / south / north -- 어느 통로로 가는 장면인가
            "store_usd": None,         # 매장 USD 경로
            "store_usd_md5": None,     # **그 USD 의 md5.**  경로가 같아도 내용이 다를 수 있다
            "store_seed": -1,          # 진열 재배치 씨앗.  -1 은 USD 가 든 배치 그대로
            "shelf_seed": -1,          # 목표 진열대 적재 씨앗.  -1 은 비워 둠
            "physics_hz": 120.0,       # 60 이면 상자를 떨어뜨린다 (CLAUDE.md 9 절)
            "floor_approx": "sdf",
            "ground_mat": "shipped",
            "desk_dynamic": True,      # 책상이 힘을 받는가.  A-3-3 이 이것을 전제한다
            "contact_sensors": True,
            "settle_steps": 300,       # sim.reset() 뒤 로봇이 가라앉는 2초를 넘기는 데 필요
            "gpu": None,               # **Blackwell 만 물리가 다르다** (CLAUDE.md 68 절)
            "isaac_version": None,
            "made_utc": None,
            "made_by": None,           # 만든 명령줄 전문
        },
        # ── 정착이 끝난 뒤 실측한 월드 자세.  여기부터는 전부 잰 값이다 ──────────────────
        "robot": {
            "prim": None,
            "root_pos": None,          # [x, y, z]
            "root_quat": None,         # [w, x, y, z]
            "joint_names": None,
            "joint_pos": None,
            "grip_links": None,        # {링크이름: {"prim":…, "pos":[…], "quat":[…]}}
        },
        "crate": {
            "prim": None, "usd": None,
            "pos": None, "quat": None,
            "size": None,              # [along, across, height]
            "mass_kg": None,
        },
        "desk": {
            "prim": None, "usd": None,
            "pos": None, "quat": None,
            "size": None,              # [x, y, z]
            "top_z": None,             # **상수로 쓰지 말 것.**  책상은 밀리기도 들리기도 한다
            "dynamic": None, "mass_kg": None,
        },
        # ── 부딪히면 안 되는 것들.  A-2-3 이 이 목록을 쓴다 ────────────────────────────
        "furniture": {
            "fixtures": None,          # [{"name":…, "bbox":[x0,y0,x1,y1], "scored":bool}]
            "skipped_note": None,      # 왜 어떤 것은 채점에서 빠지는가
            "tables": None,            # 식사공간 원형 탁상 3개 (중심, 반지름, 상판 z)
            "stools": None,            # 스툴 12개의 **배치 뒤** 실측 위치
        },
        # ── 진열된 상품.  **평가표 Preset 3 이 요구하는 랜덤이 실제로 걸렸는지가 여기 보인다** ──
        #
        # 2026-09-02 이전에는 이 블록이 없었다.  진열은 되고 있었는데 씬 파일에 안 남아서,
        # `--verify` 가 대조하지 못하고 받는 분도 랜덤인지 확인할 방법이 없었다.
        #
        # 두 진열대를 다르게 적는 이유:
        #   목표 진열대  21개뿐이고 **Isaac 없이 다시 계산된다** (`sim/shelf_stock.stock(seed)`
        #                은 순수 산술이다).  그래서 전 품목을 이름·자세까지 적고, 산술로 나온
        #                목록의 md5 도 같이 적는다 -- 받는 분이 시뮬레이터 없이 검산할 수 있다
        #   기타 진열대  수백 개이고 USD 통째 교체라 산술로 재현되지 않는다.  그래서 **기물별
        #                메시 수**만 적는다.  이것으로 "씨앗이 바뀌면 배치도 바뀐다" 와
        #                "열두 곤돌라가 다 채워졌다" 둘 다 확인된다 (39절: 참조가 깨져도 USD 는
        #                조용히 열리고, 텅 빈 곤돌라로 한 판을 다 모은 적이 있다)
        "products": {
            "target_shelf": {
                "seed": -1,
                "fixture": None,       # 목표 진열대 프림 이름
                "gaps": None,          # [[층, 칸]] -- 비워 둔 앞줄 자리.  참가자가 채울 곳
                "authored_md5": None,  # shelf_stock.stock(seed) 의 md5.  Isaac 없이 검산 가능
                "items": None,         # [{prim, name, pos, quat}] -- 정착 뒤 실측
            },
            "other_shelves": {
                "seed": -1,
                "per_fixture": None,   # {기물 이름: 메시 수}
                "total": None,
            },
        },
        "goal": {
            "xy": None, "yaw": None,
            "tol_m": None,             # 도착 허용 반경.  로봇 치수에서 나온 값
            "shelf_face_x": None,      # 목표 진열대 앞면
            "shelf_y": None,
        },
    }


def save(d, path):
    from pathlib import Path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(d, ensure_ascii=False, indent=2))


def load(path):
    from pathlib import Path
    d = json.loads(Path(path).read_text())
    if d.get("schema") != SCHEMA_VERSION:
        raise SystemExit(f"씬 파일 형식이 {d.get('schema')} 인데 이 코드는 "
                         f"{SCHEMA_VERSION} 를 읽는다")
    return d


def _vdiff(a, b):
    """두 벡터의 최대 절대 오차.  둘 중 하나라도 없으면 None."""
    if a is None or b is None:
        return None
    if len(a) != len(b):
        return float("inf")
    return max(abs(float(x) - float(y)) for x, y in zip(a, b))


def _qdiff(a, b):
    """쿼터니언 오차.  **q 와 -q 는 같은 회전이므로 가까운 쪽으로 재야 한다** -- 안 그러면
    같은 자세가 2.0 만큼 다르다고 나온다."""
    if a is None or b is None:
        return None
    d1 = _vdiff(a, b)
    d2 = _vdiff(a, [-float(x) for x in b])
    return min(d1, d2)


def compare(want, got, tol=None):
    """두 씬 파일이 같은 장면인가.  **차이 목록을 돌려주고, 통과/불통은 부르는 쪽이 정한다.**

    돌려주는 것: [(항목, 오차, 허용치, 통과여부), ...].  오차가 None 이면 한쪽에 값이 없는
    것이고, 그것은 통과가 아니다 -- **빠진 항목은 맞은 항목이 아니다**
    (`Task-A/scoring/place_gates.py:85` 과 같은 규칙).
    """
    t = dict(TOL)
    if tol:
        t.update(tol)
    rows = []

    def add(name, diff, lim):
        rows.append((name, diff, lim, diff is not None and diff <= lim))

    add("robot.root_pos", _vdiff(want["robot"]["root_pos"], got["robot"]["root_pos"]),
        t["pos_m"])
    add("robot.root_quat", _qdiff(want["robot"]["root_quat"], got["robot"]["root_quat"]),
        t["quat"])
    add("robot.joint_pos", _vdiff(want["robot"]["joint_pos"], got["robot"]["joint_pos"]),
        t["joint_rad"])
    if want["robot"]["joint_names"] != got["robot"]["joint_names"]:
        rows.append(("robot.joint_names", float("inf"), 0.0, False))
    else:
        rows.append(("robot.joint_names", 0.0, 0.0, True))

    wl = want["robot"].get("grip_links") or {}
    gl = got["robot"].get("grip_links") or {}
    for b in GRIP_LINKS:
        w, g = wl.get(b), gl.get(b)
        add(f"grip.{b}", _vdiff(w and w.get("pos"), g and g.get("pos")), t["pos_m"])

    for obj in ("crate", "desk"):
        add(f"{obj}.pos", _vdiff(want[obj]["pos"], got[obj]["pos"]), t["pos_m"])
        add(f"{obj}.quat", _qdiff(want[obj]["quat"], got[obj]["quat"]), t["quat"])
        add(f"{obj}.size", _vdiff(want[obj]["size"], got[obj]["size"]), t["size_m"])

    wt = want["desk"].get("top_z")
    gt = got["desk"].get("top_z")
    add("desk.top_z", None if (wt is None or gt is None) else abs(wt - gt), t["pos_m"])

    # 가구는 개수와 상자 좌표가 같아야 한다.  하나라도 다르면 부딪힘 판정이 달라진다.
    wf = {f["name"]: f["bbox"] for f in (want["furniture"].get("fixtures") or [])}
    gf = {f["name"]: f["bbox"] for f in (got["furniture"].get("fixtures") or [])}
    if set(wf) != set(gf):
        rows.append(("furniture.names", float("inf"), 0.0, False))
    else:
        rows.append(("furniture.names", 0.0, 0.0, True))
        worst = 0.0
        for n in wf:
            d = _vdiff(wf[n], gf[n])
            worst = max(worst, d if d is not None else float("inf"))
        add("furniture.bbox", worst, t["pos_m"])

    ws = want["furniture"].get("stools") or []
    gs = got["furniture"].get("stools") or []
    if len(ws) != len(gs):
        rows.append(("furniture.stools", float("inf"), 0.0, False))
    else:
        worst = 0.0
        for a, b in zip(ws, gs):
            d = _vdiff(a.get("xy"), b.get("xy"))
            worst = max(worst, d if d is not None else float("inf"))
        add("furniture.stools", worst, t["pos_m"])

    # ── 진열된 상품 ─────────────────────────────────────────────────────────────────
    # **씨앗이 같으면 진열도 같아야 한다.**  이 대조가 없으면 "진열 코드가 안 돌았다" 가
    # 통과로 보인다 -- 2026-09-02 에 실제로 그렇게 세 편이 빈 진열대로 렌더됐다.
    wp = (want.get("products") or {})
    gp = (got.get("products") or {})
    wt_, gt_ = wp.get("target_shelf") or {}, gp.get("target_shelf") or {}
    if wt_.get("authored_md5") is None or gt_.get("authored_md5") is None:
        rows.append(("products.target.authored_md5", None, 0.0, False))
    else:
        rows.append(("products.target.authored_md5", 0.0, 0.0,
                     wt_["authored_md5"] == gt_["authored_md5"]))
    wi, gi = wt_.get("items"), gt_.get("items")
    if not wi or not gi or len(wi) != len(gi):
        rows.append(("products.target.count", float("inf"), 0.0, False))
    else:
        rows.append(("products.target.count", 0.0, 0.0, True))
        worst_p, worst_q, names_ok = 0.0, 0.0, True
        for a, b in zip(wi, gi):
            names_ok = names_ok and a.get("name") == b.get("name") and a.get("prim") == b.get("prim")
            d = _vdiff(a.get("pos"), b.get("pos"))
            worst_p = max(worst_p, d if d is not None else float("inf"))
            d = _qdiff(a.get("quat"), b.get("quat"))
            worst_q = max(worst_q, d if d is not None else float("inf"))
        rows.append(("products.target.names", 0.0 if names_ok else float("inf"), 0.0, names_ok))
        add("products.target.pos", worst_p, t["pos_m"])
        add("products.target.quat", worst_q, t["quat"])

    wo, go = wp.get("other_shelves") or {}, gp.get("other_shelves") or {}
    wpf, gpf = wo.get("per_fixture"), go.get("per_fixture")
    if not wpf or not gpf:
        rows.append(("products.other.per_fixture", None, 0.0, False))
    else:
        rows.append(("products.other.per_fixture", 0.0, 0.0, wpf == gpf))
        # **빈 곤돌라가 있으면 그 자체로 불통이다** (39절: 참조가 깨져도 USD 는 조용히 열리고,
        # 곤돌라 열한 개가 텅 빈 채로 한 판을 다 모은 적이 있다).
        #
        # 곤돌라만 본다.  `Walls` / `Dome` / `Key` 는 메시가 0 인 것이 정상이다 -- 벽은 매장
        # 범위 밖 슬래브이고 나머지는 조명·표식이다 (실측 2026-09-02: 32개 기물 중 이 셋만 0).
        gond = {k: int(v) for k, v in gpf.items() if "gondola" in k}
        rows.append(("products.other.gondolas", 0.0 if len(gond) == 12 else float("inf"),
                     0.0, len(gond) == 12))
        rows.append(("products.other.none_empty", 0.0, 0.0,
                     bool(gond) and all(v > 0 for v in gond.values())))

    add("goal.xy", _vdiff(want["goal"]["xy"], got["goal"]["xy"]), t["pos_m"])
    wy, gy = want["goal"].get("yaw"), got["goal"].get("yaw")
    add("goal.yaw", None if (wy is None or gy is None)
        else abs(math.atan2(math.sin(wy - gy), math.cos(wy - gy))), t["quat"])
    return rows


def render(rows):
    """대조 결과를 사람이 읽는 표로.  **통과해도 최대 오차를 찍는다.**"""
    out = []
    bad = 0
    for name, diff, lim, ok in rows:
        if not ok:
            bad += 1
        shown = "없음" if diff is None else (f"{diff:.3e}" if diff != float("inf") else "다름")
        out.append(f"  {'O' if ok else 'X'}  {name:34} 오차 {shown:>10}  허용 {lim:.0e}")
    out.append("")
    out.append(f"항목 {len(rows)}개 중 {len(rows) - bad}개 일치"
               + ("" if bad == 0 else f", {bad}개 불일치"))
    return "\n".join(out)
