# Copyright 2026.
#
# 스캐너 카메라로 QR 을 실제로 읽는다. 평가표가 요구하는 판독 방식이다 --
# 「판독은 스캐너 카메라 이미지로 한다. 실물 스캐너가 보는 것과 같은 시점이어야 하므로
# 다른 카메라를 쓰지 않는다. 디코더가 그 시도 상품의 기대 코드 문자열을 반환해야 한다.」
#
# **매 프레임 읽지 않는다.** 렌더가 비싸고, 실물 스캐너도 늘 읽고 있지 않다.
#
#     1  기하 게이트   기존 인식 조건을 1.5 배로 넓혀 대기한다. 여기 들어와야 다음으로 간다
#     2  이미지 판독   그 프레임만 스캐너캠을 렌더해 디코드한다
#     3  냉각          한 번 읽히면 5 초 동안 판독기를 끈다. 게이트를 벗어나도 끈다
#
# 카메라 사양은 수집 파이프라인의 `ScanCam` 을 그대로 옮겼다(QR-136): 800x500,
# focal 31.43 mm, 조리개 20.955 / 13.097 mm. 방출점 15 cm 에서 가로 8 x 세로 5 cm 를
# 보는 방사형 빔 사양이다. 눈은 빔 출발선 앞 3 cm, 겨눔점은 30 cm 앞이다.

import os

__all__ = ["SCAN_CAM", "QrReader", "scan_cam_cfg"]

# (폭, 높이, 초점거리 mm, 가로조리개 mm, 세로조리개 mm, 눈 거리 m, 겨눔 거리 m)
SCAN_CAM = (800, 500, 31.43, 20.955, 13.097, 0.03, 0.30)


def scan_cam_cfg():
    """`CameraCfg` 를 만든다. Isaac 이 있는 곳에서만 부른다."""
    import isaaclab.sim as sim_utils
    from isaaclab.sensors import CameraCfg
    w, h, foc, ha, va, _, _ = SCAN_CAM
    return CameraCfg(
        prim_path="{ENV_REGEX_NS}/ScanCam", update_period=0.0,
        height=h, width=w, data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(focal_length=foc, horizontal_aperture=ha,
                                         vertical_aperture=va, clipping_range=(0.02, 5.0)))


class QrReader:
    """게이트를 넘긴 프레임에서만 스캐너캠을 읽는다."""

    def __init__(self, cam, expect_by_slug, log=None, gate_mul=None,
                 cooldown_s=None, render_n=None):
        self.cam = cam
        self.expect = dict(expect_by_slug)
        self._log = log or (lambda m: None)
        # 게이트 배율. 기하 인식의 횡이탈 한계를 이만큼 넓혀 「읽어 볼 만한 자리」로 삼는다.
        self.gate_mul = float(os.environ.get("TASKC_QR_GATE_MUL", gate_mul or 1.5))
        # 한 번 읽으면 이만큼 쉰다. 같은 상품을 연달아 읽어 로그가 넘치는 것을 막는다.
        self.cooldown = float(os.environ.get("TASKC_QR_COOLDOWN_S", cooldown_s or 5.0))
        # 판독 직전 RTX 를 수렴시키는 렌더 횟수. 적으면 얼룩진 그림을 읽는다.
        self.render_n = int(os.environ.get("TASKC_QR_RENDER_N", render_n or 8))
        self.events = []
        self._off_until = -1.0      # 이 시각까지는 끈다
        self._tries = 0

    def _place(self, sim, b0, bd):
        import torch
        _, _, _, _, _, d_eye, d_tgt = SCAN_CAM
        eye = [float(b0[i] + bd[i] * d_eye) for i in range(3)]
        tgt = [float(b0[i] + bd[i] * d_tgt) for i in range(3)]
        dev = sim.device
        self.cam.set_world_poses_from_view(
            torch.tensor([eye], dtype=torch.float32, device=dev),
            torch.tensor([tgt], dtype=torch.float32, device=dev))

    def try_read(self, sim, b0, bd, slug, t, in_gate):
        """게이트 안이면 한 프레임 읽는다. 읽히면 `(코드, 맞았나)`, 아니면 None."""
        if self.cam is None or not in_gate or t < self._off_until:
            return None
        try:
            import numpy as np
            import zxingcpp
            self._place(sim, b0, bd)
            for _ in range(self.render_n):
                sim.render()
            self.cam.update(0.0)
            img = np.asarray(self.cam.data.output["rgb"][0, ..., :3].cpu(), dtype=np.uint8)
            res = zxingcpp.read_barcodes(img)
            self._tries += 1
            if not res:
                return None
            text = res[0].text
            ok = bool(text and text == self.expect.get(slug))
            self._off_until = t + self.cooldown
            self.events.append(dict(ok=ok, slug=slug, t=round(float(t), 3), text=text))
            self._log("[QR] %s %s (%s)  -- %.0f초 쉼"
                      % (slug, "판독 O" if ok else "다른 값", text, self.cooldown))
            return (text, ok)
        except Exception as e:
            self._log("[QR] 판독 불가: %r" % (e,))
            return None

    def report(self):
        return {"decode": self.events, "tries": self._tries,
                "gate_mul": self.gate_mul, "cooldown_s": self.cooldown}
