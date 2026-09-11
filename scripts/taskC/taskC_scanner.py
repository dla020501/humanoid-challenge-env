# Copyright 2026.
#
# 스캐너의 겉모습. 물리·판독·재생 로직에는 손대지 않고 재질과 후처리만 다룬다.
#
# 밀(v5, `qr_sweep_replay.py`)이 기록할 때 실제로 켜 두었던 세 가지를 그대로 옮긴 것이다.
# 기록판 로그(`gt_final/<시드>/<시드>_chain.log`)가 쓴 값을 남겨 두었다:
#
#     [RPL] V4-305 광채 op,enabled,scale,threshold (세기 8.0 임계 0.05)
#     [RPL] V4-28 스캐너 다크 도색 (0.018,0.018,0.022) 메시 1개
#     [RPL] V4-194 스캐너 LED 준비 (색 [0.12, 0.8, 0.08], 강도 6000.0,
#                                   상시 점등 / 판독 시 3회 0.5s 깜빡임)
#     [RPL] v5-5b LED 블럭 정사각 7x7mm 두께 0.5mm
#     [RPL] V4-346 스캐너 빨간 점 ON (r 3mm, 사출점 기준 -8/+0/-1mm)
#     [RPL] V4-346b 빨간 점 HDR 발광 (색 1.0,0.03,0.0, 강도 12000)
#
# 세기 8.0 / 임계 0.05 는 v5 소스의 기본값(4.0 / 0.3)이 아니라 기록판이 환경변수로 준
# 값이다. 기본값을 쓰면 광채가 약해 GT 와 다른 그림이 된다.

import math
import os

__all__ = ["enable_glow", "paint_dark", "bind_led", "add_window_dot", "ScannerLed"]

SCANNER_PRIM = "/World/envs/env_0/Scanner"


def _noop(*_a, **_k):
    pass


def enable_glow(log=None):
    """V4-305: 발광면을 '빛'으로 보이게 하는 화면 후처리.

    발광 세기만으로는 그냥 밝은 면일 뿐이라는 것이 v5 실측이다. 화면 공간 후처리라
    장면 복잡도와 무관하게 화면당 고정 비용이다.

    V4-320 이 AA 를 FXAA(op 2)로 바꾸는 것도 같이 옮긴다. 시간 누적 AA 는 발광이 꺼져도
    직전 프레임이 섞여 잔상이 남아 제자리 점멸이 "안 꺼진 것"처럼 보인다.
    """
    log = log or _noop
    try:
        import carb
        cs = carb.settings.get_settings()
        done = []
        for key, val in (
                ("/rtx/post/aa/op", int(os.environ.get("TASKC_RTX_AA", "2"))),
                ("/rtx/post/bloom/enabled", True),
                ("/rtx/post/bloom/scale", float(os.environ.get("TASKC_BLOOM_SCALE", "8.0"))),
                ("/rtx/post/bloom/threshold", float(os.environ.get("TASKC_BLOOM_THRESH", "0.05")))):
            try:
                cs.set(key, val)
                done.append(key.rsplit("/", 1)[-1])
            except Exception:
                pass
        log("V4-305 광채 %s (세기 %s 임계 %s)"
            % (",".join(done), os.environ.get("TASKC_BLOOM_SCALE", "8.0"),
               os.environ.get("TASKC_BLOOM_THRESH", "0.05")))
    except Exception as e:
        log("V4-305 광채 실패: %r" % (e,))


def paint_dark(stage, prim_path=SCANNER_PRIM, log=None):
    """V4-28: 스캐너 몸통을 거의 순검정으로 도색한다.

    **메시 프림마다 직접** 바인딩한다. 프림 전체에 '자식보다 강한' 바인딩을 걸면
    LED 서브셋(`GeomSubset 'Led'`)까지 덮어써서 LED 가 안 보인다 (V4-194 에서 확인된 함정).
    """
    log = log or _noop
    spec = os.environ.get("TASKC_SCANNER_COLOR", "0.018,0.018,0.022")
    if not spec:
        return
    try:
        from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf
        prim = stage.GetPrimAtPath(prim_path)
        if not (prim and prim.IsValid()):
            log("V4-28 스캐너 프림 없음 -- 건너뜀")
            return
        r, g, b = [float(v) for v in spec.split(",")]
        mat = UsdShade.Material.Define(stage, "/World/Looks/ScannerDark28")
        shd = UsdShade.Shader.Define(stage, "/World/Looks/ScannerDark28/Shader")
        shd.CreateIdAttr("UsdPreviewSurface")
        shd.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(r, g, b))
        shd.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(
            float(os.environ.get("TASKC_SCANNER_ROUGH", "0.35")))
        shd.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.1)
        mat.CreateSurfaceOutput().ConnectToSource(shd.ConnectableAPI(), "surface")
        n = 0
        for p in Usd.PrimRange(prim):
            if p.IsA(UsdGeom.Mesh):
                UsdShade.MaterialBindingAPI.Apply(p).Bind(mat)
                n += 1
        log("V4-28 스캐너 다크 도색 (%s) 메시 %d개" % (spec, n))
    except Exception as e:
        log("V4-28 도색 불가: %r" % (e,))


class ScannerLed:
    """V4-194: 스캐너 상부 창의 초록 LED.

    **평상시 항상 켜져 있고**, 기대 코드를 실제로 판독한 순간 0.5 초 동안 3 번 깜빡인 뒤
    다시 상시 점등으로 돌아온다. 재질 속성만 바꾸므로 물리·판독에 영향이 없다.

    한 주기는 `blink_s / blink_n` 이고 앞 절반이 소등, 뒤 절반이 점등이다.
    쓰는 쪽은 판독 순간 `blink()` 를, 물리 스텝마다 `tick(dt)` 를 부르면 된다.
    """

    def __init__(self, shader, intensity, blink_n, blink_s, log=None):
        self._shader = shader
        self._I = float(intensity)
        self._n = max(1, int(blink_n))
        self._s = float(blink_s)
        self._log = log or _noop
        self._t = 0.0
        self._t_b = 0.0
        self._blinking = False
        self._count = 0

    def _set(self, v):
        if self._shader is not None:
            self._shader.GetInput("emissive_intensity").Set(float(v))

    def blink(self):
        """판독 성공 순간 -- 깜빡임 시작."""
        if self._shader is None:
            return
        self._count += 1
        self._blinking = True
        self._t_b = self._t
        self._log("V4-194 LED 깜빡임 #%d (sim t=%.2fs, %d회 / %ss)"
                  % (self._count, self._t, self._n, self._s))

    def tick(self, dt):
        """물리 스텝마다. 깜빡임이 끝나면 상시 점등으로 복귀한다."""
        self._t += float(dt)
        if not self._blinking:
            return
        e = self._t - self._t_b
        if e >= self._s:
            self._set(self._I)
            self._blinking = False
            return
        period = self._s / self._n
        self._set(0.0 if (e % period) / period < 0.5 else self._I)

    @property
    def sim_time(self):
        return self._t


def bind_led(stage, prim_path=SCANNER_PRIM, log=None):
    """`scanner_taskC.usd` 의 `GeomSubset 'Led'` 에 OmniPBR 발광 재질을 바인딩한다.

    `TASKC_LED=0` 으로 끈다. 반환값은 `ScannerLed` 이고, 끄거나 실패하면 `None` 이다.
    """
    log = log or _noop
    if os.environ.get("TASKC_LED", "1") != "1":
        return None
    try:
        from pxr import Usd, UsdShade, Sdf, Gf
        prim = stage.GetPrimAtPath(prim_path)
        if not (prim and prim.IsValid()):
            log("V4-194 스캐너 프림 없음 -- 건너뜀")
            return None
        subset = None
        for p in Usd.PrimRange(prim):
            if p.GetTypeName() == "GeomSubset" and p.GetName() == "Led":
                subset = p
                break
        if subset is None:
            log("V4-194 GeomSubset 'Led' 없음 -- scanner_taskC.usd 갱신 필요")
            return None
        color = [float(v) for v in os.environ.get("TASKC_LED_COLOR", "0.12,0.80,0.08").split(",")]
        intensity = float(os.environ.get("TASKC_LED_INTENSITY", "6000"))
        mat = UsdShade.Material.Define(stage, "/World/Looks/ScannerLed194")
        shd = UsdShade.Shader.Define(stage, "/World/Looks/ScannerLed194/Shader")
        shd.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)
        shd.SetSourceAsset(Sdf.AssetPath("OmniPBR.mdl"), "mdl")
        shd.SetSourceAssetSubIdentifier("OmniPBR", "mdl")
        # V4-202: 소등 시 무채색 근검정. 초록 확산색을 두면 꺼져도 초록으로 보인다.
        shd.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(0.010, 0.011, 0.010))
        shd.CreateInput("reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(0.30)
        shd.CreateInput("metallic_constant", Sdf.ValueTypeNames.Float).Set(0.0)
        shd.CreateInput("enable_emission", Sdf.ValueTypeNames.Bool).Set(True)
        shd.CreateInput("emissive_color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
        shd.CreateInput("emissive_intensity", Sdf.ValueTypeNames.Float).Set(intensity)
        mat.CreateSurfaceOutput("mdl").ConnectToSource(shd.ConnectableAPI(), "out")
        mat.CreateDisplacementOutput("mdl").ConnectToSource(shd.ConnectableAPI(), "out")
        mat.CreateVolumeOutput("mdl").ConnectToSource(shd.ConnectableAPI(), "out")
        UsdShade.MaterialBindingAPI.Apply(subset).Bind(mat)
        n = max(1, int(os.environ.get("TASKC_LED_BLINK_N", "3")))
        s = float(os.environ.get("TASKC_LED_BLINK_S", "0.5"))
        log("V4-194 스캐너 LED 준비 (색 %s, 강도 %s, 상시 점등 / 판독 시 %d회 %ss 깜빡임)"
            % (color, intensity, n, s))
        return ScannerLed(shd, intensity, n, s, log=log)
    except Exception as e:
        log("V4-194 LED 불가: %r" % (e,))
        return None


def add_window_dot(stage, emit_local, prim_path=SCANNER_PRIM, log=None):
    """V4-346: 스캐너 창의 빨간 레이저 개구. 사출점 왼쪽에 붙는 납작한 정육면체다.

    스캐너 프림의 **자식**으로 만들기 때문에 오른손 용접을 저절로 따라간다. 프림 하나에
    발광 재질뿐이라 비용은 없다시피 하다.

    재질은 OmniPBR 로 간다(V4-346b). PreviewSurface 는 채널당 1.0 이 상한이라 발광 배율을
    주면 빨강이 핑크로 뜬다.

    `TASKC_LED_DOT=0` 으로 끈다. 수집 파이프라인(v5)의 기본값은 0 이므로, 동봉된 학습
    데이터와 그림을 정확히 맞추려면 0 으로 두면 된다.
    """
    log = log or _noop
    if os.environ.get("TASKC_LED_DOT", "1") != "1":
        return None
    try:
        import isaaclab.sim as sim_utils
        from pxr import UsdShade, Sdf, Gf
        side = float(os.environ.get("TASKC_LED_DOT_SIDE_MM", "7")) / 1000.0
        thick = float(os.environ.get("TASKC_LED_DOT_T_MM", "0.5")) / 1000.0
        dx = float(os.environ.get("TASKC_LED_DOT_DX_MM", "-8")) / 1000.0
        dy = float(os.environ.get("TASKC_LED_DOT_DY_MM", "0")) / 1000.0
        dz = float(os.environ.get("TASKC_LED_DOT_DZ_MM", "-1")) / 1000.0
        rgb = tuple(float(v) for v in
                    os.environ.get("TASKC_LED_DOT_RGB", "1.0,0.03,0.0").split(","))
        intensity = float(os.environ.get("TASKC_LED_DOT_INTENSITY", "12000"))
        dot_path = prim_path + "/LedDot"
        cfg = sim_utils.CuboidCfg(
            size=(side, side, thick),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=rgb, roughness=0.4))
        cfg.func(dot_path, cfg,
                 translation=(float(emit_local[0]) + dx,
                              float(emit_local[1]) + dy,
                              float(emit_local[2]) + dz - thick / 2))
        mat = UsdShade.Material.Define(stage, "/World/Looks/LedDot346")
        shd = UsdShade.Shader.Define(stage, "/World/Looks/LedDot346/Shader")
        shd.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)
        shd.SetSourceAsset(Sdf.AssetPath("OmniPBR.mdl"), "mdl")
        shd.SetSourceAssetSubIdentifier("OmniPBR", "mdl")
        shd.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(0.2, 0.0, 0.0))
        shd.CreateInput("reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(0.30)
        shd.CreateInput("metallic_constant", Sdf.ValueTypeNames.Float).Set(0.0)
        shd.CreateInput("enable_emission", Sdf.ValueTypeNames.Bool).Set(True)
        shd.CreateInput("emissive_color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
        shd.CreateInput("emissive_intensity", Sdf.ValueTypeNames.Float).Set(intensity)
        mat.CreateSurfaceOutput("mdl").ConnectToSource(shd.ConnectableAPI(), "out")
        mat.CreateDisplacementOutput("mdl").ConnectToSource(shd.ConnectableAPI(), "out")
        mat.CreateVolumeOutput("mdl").ConnectToSource(shd.ConnectableAPI(), "out")
        dot = stage.GetPrimAtPath(dot_path)
        UsdShade.MaterialBindingAPI.Apply(dot).Bind(mat, UsdShade.Tokens.strongerThanDescendants)
        log("v5-5b LED 블럭 정사각 %.0fx%.0fmm 두께 %.1fmm" % (side * 1000, side * 1000, thick * 1000))
        log("V4-346 스캐너 빨간 점 ON (사출점 기준 %+.0f/%+.0f/%+.0fmm, 색 %s, 강도 %.0f)"
            % (dx * 1000, dy * 1000, dz * 1000, list(rgb), intensity))
        return dot_path
    except Exception as e:
        log("V4-346 빨간 점 불가: %r" % (e,))
        return None
