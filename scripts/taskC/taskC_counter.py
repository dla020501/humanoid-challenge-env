# Copyright 2026.
#
# 계산대 위의 장면 손질 -- Isaac 이 뜬 뒤에만 쓸 수 있는 것들.
#
#   draw_band                 상품이 놓이는 빨간 띠를 상판에 테이프 한 줄로 그린다. 시각 전용
#                             (콜라이더 없음). 수집 파이프라인의 `taskC/tape.py::draw_rect` 와
#                             같은 방식·같은 두께 -- 학습 데이터에 찍힌 띠와 참가자가 보는 띠가
#                             같아야 한다.
#   deactivate_duplicates     구워진 매장 USD 에 놓여 있는 정적 스캐너 소품과 계산대 옆 바구니를
#                             끈다. 과제 C 는 스캐너를 로봇이 드는 강체로 따로 스폰하므로, 끄지 않으면
#                             장면에 스캐너가 둘이 된다. 바구니는 수집 파이프라인이 끄고 찍었으므로
#                             (V4-235) 여기서도 끈다. USD 를 고치지 않고 스테이지에서만 비활성화한다.
#   remove_low_shelf          계산대 직원 쪽 맨 아래 선반판(바닥 위 0.104~0.138 m)을 메시에서
#                             잘라낸다. 로봇이 계산대 앞에 바짝 설 때 섀시가 이 판에 올라타
#                             기울어지므로, 수집 파이프라인(taskC/counter_edit.py)과 같은 방식으로
#                             면 단위로 지운다. InteractiveScene 이 prim 을 만든 뒤, sim.reset()
#                             이 콜라이더를 굽기 **전에** 불러야 한다.
#
# 이 파일은 pxr 과 isaaclab 을 쓴다. 데모가 AppLauncher **뒤에서** 읽는다.

import isaaclab.sim as sim_utils

from . import taskC_layout as L


def _strips(x0, x1, y0, y1, w):
    """사각형 테두리를 테이프 폭 w 의 막대 넷으로. (cx, cy, lx, ly) 세계 좌표."""
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    lx, ly = (x1 - x0), (y1 - y0)
    # 막대 넷 중 **로봇 좌표의 y 끝(= 세계 x 끝)에 놓이는 둘만 테이프 폭의 두 배만큼 짧다.**
    # 수집 파이프라인 `kit_config.tape_strips` 가 그렇게 놓는다 (같은 파일 444~457):
    #
    #     (x0 + w/2, cy, w, sy)          near side  -- 전체 길이
    #     (x1 - w/2, cy, w, sy)          far side   -- 전체 길이
    #     (cx, y0 + w/2, sx - 2*w, w)    right side -- 2*w 짧다
    #     (cx, y1 - w/2, sx - 2*w, w)    left side  -- 2*w 짧다
    #
    # 넷 다 전체 길이로 놓으면 네 모서리에서 막대가 두 겹으로 겹쳐, 그 자리만 두껍고 밝게
    # 보인다. 여기 좌표는 세계 축이고 로봇이 요 90 도로 서 있으므로 로봇 x <-> 세계 y 다.
    return [
        (cx, y0 + w / 2.0, lx, w),                  # 세계 y0 (로봇 x 끝) -- 전체 길이
        (cx, y1 - w / 2.0, lx, w),                  # 세계 y1 (로봇 x 끝) -- 전체 길이
        (x0 + w / 2.0, cy, w, ly - 2.0 * w),        # 세계 x0 (로봇 y 끝) -- 2*w 짧다
        (x1 - w / 2.0, cy, w, ly - 2.0 * w),        # 세계 x1 (로봇 y 끝) -- 2*w 짧다
    ]


def band_world_rect():
    """로봇 좌표의 띠 [x0,x1]x[y0,y1] 를 세계 좌표 축정렬 사각형 (x0, x1, y0, y1) 으로.

    로봇을 `L.BASE_BACK` 만큼 뒤로 물렸으므로, 띠를 로봇 좌표 그대로 그리면 계산대 위에서도
    같은 만큼 따라 밀린다. 띠는 계산대에 붙은 표시이지 로봇에 붙은 것이 아니므로 그만큼 앞으로
    되돌려, 계산대 기준 자리를 학습 데이터와 같게 둔다 (로봇 +x 가 계산대 쪽).
    """
    a = L.scene_to_world((L.BAND["x0"], L.BAND["y0"]))
    b = L.scene_to_world((L.BAND["x1"], L.BAND["y1"]))
    return (min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1]))


def draw_band(env_prim="/World/envs/env_0", name="band", z_lift=0.0006, log=print):
    """빨간 띠를 상판 위에 그린다. sim.reset() 뒤에 부른다 (장면 장식이지 물리 물체가 아니다)."""
    x0, x1, y0, y1 = band_world_rect()
    for k, (cx, cy, lx, ly) in enumerate(_strips(x0, x1, y0, y1, L.TAPE_W)):
        cfg = sim_utils.CuboidCfg(
            size=(float(lx), float(ly), float(L.TAPE_T)),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=L.TAPE_COLOR, roughness=0.9))
        cfg.func(f"{env_prim}/Tape_{name}_{k}", cfg,
                 translation=(float(cx), float(cy), float(L.COUNTER_TOP_Z + L.TAPE_T / 2.0 + z_lift)))
    log(f"[TAPE] {name}  세계 x[{x0:.3f},{x1:.3f}]  y[{y0:.3f},{y1:.3f}]  "
        f"{(x1 - x0) * 100:.0f}(x) x {(y1 - y0) * 100:.0f}(y) cm, 테이프 {L.TAPE_W * 1000:.0f} mm")


def bind_band_idle(stage, env_prim="/World/envs/env_0", name="band",
                   rgb=(0.3, 0.3, 0.3), intensity=0.0, log=print):
    """띠 네 막대에 **회색 발광 재질**을 입힌다. 수집 파이프라인 v5-3d 그대로다.

    그쪽은 띠를 빨강(0.80, 0.03, 0.03)으로 그린 **직후** 이 재질을 덮어씌운다 -- 주석 그대로
    "인식 전 초반 빨강 방지". 그래서 학습 데이터의 띠는 평소 **회색**이고, 상품을 읽는 순간에만
    6 초 빨강으로 바뀐다(v5-3c). 이 단계가 없으면 띠가 처음부터 끝까지 빨갛게 남는다.

    `sim.reset()` 과 `draw_band` 뒤에 부른다 (막대 프림이 있어야 바인딩된다).

    바인딩된 셰이더를 돌려준다 -- 인식 순간 빨강으로 바꾸는 쪽(`taskC_beam.BandLight`)이
    이걸 받아 색만 갈아 끼운다. 하나도 못 붙였으면 `None` 이다.
    """
    from pxr import UsdShade, Sdf, Gf
    mat = UsdShade.Material.Define(stage, "/World/Looks/BandIdle")
    shd = UsdShade.Shader.Define(stage, "/World/Looks/BandIdle/Shader")
    shd.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)
    shd.SetSourceAsset(Sdf.AssetPath("OmniPBR.mdl"), "mdl")
    shd.SetSourceAssetSubIdentifier("OmniPBR", "mdl")
    shd.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
    shd.CreateInput("reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(0.9)
    shd.CreateInput("metallic_constant", Sdf.ValueTypeNames.Float).Set(0.0)
    shd.CreateInput("enable_emission", Sdf.ValueTypeNames.Bool).Set(True)
    shd.CreateInput("emissive_color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
    shd.CreateInput("emissive_intensity", Sdf.ValueTypeNames.Float).Set(float(intensity))
    for out in ("mdl",):
        mat.CreateSurfaceOutput(out).ConnectToSource(shd.ConnectableAPI(), "out")
        mat.CreateDisplacementOutput(out).ConnectToSource(shd.ConnectableAPI(), "out")
        mat.CreateVolumeOutput(out).ConnectToSource(shd.ConnectableAPI(), "out")
    n = 0
    for k in range(4):
        prim = stage.GetPrimAtPath(f"{env_prim}/Tape_{name}_{k}")
        if prim and prim.IsValid():
            UsdShade.MaterialBindingAPI.Apply(prim).Bind(
                mat, UsdShade.Tokens.strongerThanDescendants)
            n += 1
    log(f"[TAPE] 띠 평소 재질 {n}/4 (회색 {rgb} 발광 {intensity:.0f})")
    return shd if n else None


def deactivate_duplicates(stage, store_prim="/World/envs/env_0/Store", log=print):
    """매장 USD 안의 정적 스캐너와 바구니 prim 을 끈다. 끈 prim 수를 돌려준다. sim.reset() 앞에서 부른다.

    계산대(cash_table)는 끄지 않는다 -- 이 데모는 매장에 구워진 계산대를 그대로 쓴다.
    """
    root = stage.GetPrimAtPath(store_prim)
    if not root or not root.IsValid():
        log(f"[STORE] {store_prim} 가 없다 -- 중복 집기 비활성화 건너뜀")
        return 0
    n = 0
    from pxr import Usd
    for prim in Usd.PrimRange(root):
        if not prim.IsActive():
            continue
        nm = prim.GetName().lower()
        if prim.GetParent().GetName() != root.GetName():
            continue                     # 매장 바로 아래 집기만 본다 (안쪽 링크 이름은 건드리지 않는다)
        if "scanner" in nm or "big_basket" in nm or nm.endswith("basket"):
            prim.SetActive(False)
            n += 1
            log(f"[STORE] 비활성화: {prim.GetPath()}")
    return n


BOARD_Z = (0.09, 0.15)          # 실측 0.104..0.138 m 판, 양쪽으로 조금 여유
COUNTER_MESHES = ("MainTable_link/visuals/MainTable",
                  "MainTable_link/collisions/MainTable_link_col_0")


def remove_low_shelf(stage, counter_prim="/World/envs/env_0/Store/Fix_cash_table",
                     z_band=BOARD_Z, log=print):
    """계산대 맨 아래 선반판의 면을 지운다. 메시별로 지운 면 수를 돌려준다.

    선반은 MainTable 메시 안의 기하이지 prim 이 아니라서 끌 수 없고 잘라내야 한다. 면 전체가
    z 띠 안에 있을 때만 판으로 본다 -- 띠를 가로지르는 면은 옆 판이라 지우면 구멍이 난다.
    """
    import numpy as np
    from pxr import Usd, UsdGeom

    out = {}
    for rel in COUNTER_MESHES:
        prim = stage.GetPrimAtPath(f"{counter_prim}/{rel}")
        if not prim or not prim.IsValid():
            log(f"[EDIT] {rel}: 없음 -- 건너뜀")
            continue
        mesh = UsdGeom.Mesh(prim)
        pts = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
        idx = np.asarray(mesh.GetFaceVertexIndicesAttr().Get())
        cnt = np.asarray(mesh.GetFaceVertexCountsAttr().Get())
        M = np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        world = pts @ M[:3, :3] + M[3, :3]          # USD 는 행벡터: p @ M
        keep_idx, keep_cnt, dropped, k = [], [], 0, 0
        for c in cnt:
            face = idx[k:k + c]
            k += c
            z = world[face, 2]
            if z.min() >= z_band[0] and z.max() <= z_band[1]:
                dropped += 1
                continue
            keep_idx.extend(int(v) for v in face)
            keep_cnt.append(int(c))
        mesh.GetFaceVertexIndicesAttr().Set(keep_idx)
        mesh.GetFaceVertexCountsAttr().Set(keep_cnt)
        out[rel] = dropped
        log(f"[EDIT] {rel}: {len(cnt)} 면 중 {dropped} 면 제거 (z {z_band[0]:.2f}..{z_band[1]:.2f})")
    return out
