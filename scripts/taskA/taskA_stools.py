# 배포용 정본 -- 대회 환경 저장소 `Task-A/sim/stools.py` 에서 그대로 옮겼다.
# 한 줄도 고치지 않았다. 배포 이미지에는 `Task-A/` 가 없으므로 참가자 데모가 읽을 수 있는
# 자리로 옮겼을 뿐이다. 아래는 원본의 기록 그대로다.
#
# 이 파일이 없으면 안 되는 이유는 시식 스툴이다: 매장은 `eatin_r` 키트로 지어지고 그 키트는 스툴을
# 시드마다 다른 각도로 떨어뜨린다. 정돈하지 않으면 두 개가 로봇이 스폰할 좌석에 걸터앉는다.
# ---------------------------------------------------------------------------------------------

# Copyright 2025.
#
# Move the eat-in stools, before the simulation starts.
#
# Lifted out of eatin_spawn_stream.py so that every scene arranges them the same way. teleop_pick.py
# did not arrange them at all, and the robot could not get to the table -- the store's own `eatin_r`
# kit drops them at a per-seed random rotation, which regularly leaves two of them straddling the
# seat the robot spawns at.
#
# TWO THINGS THAT ARE NOT OBVIOUS AND COST A DAY EACH
#
#   The prim to move is `Stool_N`, not the mesh inside it. measure_eatin.py recorded the geometry
#   prim -- `.../Stool_2/Fix/Src/<hash>_fbx` -- and a transform authored that deep, inside a
#   reference, is silently ignored: twelve moves written, twelve stools unmoved.
#
#   It has to happen BEFORE sim.reset(). Once the stage is handed to Fabric the renderer stops
#   honouring authored USD transforms, so a stool moved mid-run stays where the picture had it.

import math

from pxr import Gf, Usd, UsdGeom


def scene_path(raw: str) -> str:
    """The measured path rebased under the spawned store."""
    return raw.replace("/World/", "/World/envs/env_0/Store/", 1)


def stool_root(raw: str) -> str:
    """The stool's own xform: everything below `Stool_N` is geometry inside a reference."""
    marker = "/Stool_"
    i = raw.find(marker)
    if i < 0:
        return raw
    j = raw.find("/", i + len(marker))
    return raw if j < 0 else raw[:j]


class Stools:
    """Attaches one extra translate op per stool and drives it to an absolute place."""

    def __init__(self, stage, seats, log=print):
        self.stage, self.log = stage, log
        self.ops, self.home = {}, {}
        for seat in seats:
            for path in seat["stool_paths"]:
                if path in self.ops:
                    continue
                prim = stage.GetPrimAtPath(scene_path(stool_root(path)))
                if not prim or not prim.IsValid():
                    log(f"!! 스툴 prim 없음: {path}")
                    continue
                xf = UsdGeom.Xformable(prim)
                op = xf.AddTranslateOp(opSuffix="seatShift")
                # Prepended: the first op is the outermost, so a leading translate is a world
                # offset for a prim whose parents are identity -- which these are.
                xf.SetXformOpOrder([op] + [o for o in xf.GetOrderedXformOps() if o != op])
                self.ops[path] = op

    def measure_home(self):
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
        for path in self.ops:
            r = cache.ComputeWorldBound(
                self.stage.GetPrimAtPath(scene_path(stool_root(path)))).ComputeAlignedRange()
            lo, hi = r.GetMin(), r.GetMax()
            self.home[path] = ((lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0)

    def place(self, seat) -> bool:
        """Put this seat's four stools where the seat says, and confirm each actually moved."""
        self.placed = seat
        moved = stuck = 0
        for j, path in enumerate(seat["stool_paths"]):
            want = seat["stool_tidy_xy"][j]
            home = self.home.get(path)
            if home is None or path not in self.ops:
                continue
            self.ops[path].Set(Gf.Vec3d(want[0] - home[0], want[1] - home[1], 0.0))
            cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
            r = cache.ComputeWorldBound(
                self.stage.GetPrimAtPath(scene_path(stool_root(path)))).ComputeAlignedRange()
            lo, hi = r.GetMin(), r.GetMax()
            cx, cy = (lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0
            if math.hypot(cx - want[0], cy - want[1]) < 0.05:
                moved += 1
            else:
                stuck += 1
                self.log(f"!! 스툴 안 움직임: {path}")
        self.log(f"스툴 배치: {moved}개 확인, {stuck}개 실패")
        return stuck == 0

    def park_others(self, seats, keep_index: int):
        """Shove every OTHER table's stools to their own seat-0 layout, so nothing is left in the
        kit's random spot where a later screenshot would show it overlapping a table.

        `keep_index` MUST be the seat `place()` was just called with. This method re-places every
        stool that is not on the kept seat's table, so naming a seat on a different table silently
        overwrites the layout `place()` just wrote -- and the caller sees nothing, because the
        stools do move, just to the wrong seat's arrangement. `carry_episode.py` did exactly that
        for one afternoon (2026-08-18) and the symptom was a crate at z 1.4 m, not a stool
        complaint. Hence the check rather than a comment.
        """
        if getattr(self, "placed", None) is not None:
            # (table, seat) as a pair -- `seat_index` alone is 0..3 WITHIN a table, so comparing
            # it by itself calls seat 0 and seat 4 the same seat, which is the exact pair this
            # check exists to separate.
            want = (int(self.placed["table_index"]), int(self.placed["seat_index"]))
            got = (int(seats[keep_index]["table_index"]), int(seats[keep_index]["seat_index"]))
            if want != got:
                self.log(f"!! 스툴 정리 좌석 불일치: place 는 테이블{want[0]}·좌석{want[1]}, "
                         f"park_others 는 테이블{got[0]}·좌석{got[1]} — 방금 놓은 배치를 덮어쓴다")
        done = set(seats[keep_index]["stool_paths"])
        for k, seat in enumerate(seats):
            if seat["table_index"] == seats[keep_index]["table_index"]:
                continue
            for j, path in enumerate(seat["stool_paths"]):
                if path in done:
                    continue
                done.add(path)
                # `stool_idle_xy`, NOT `stool_tidy_xy`. The tidy layout is the far-side-of-the-seat
                # one, and every table shares the same four seat angles, so asking each idle table
                # for a tidy layout gave all three tables the same arrangement in the same
                # 80-degree window. The idle layout scatters round the whole rim, seeded per table.
                want = seat.get("stool_idle_xy", seat["stool_tidy_xy"])[j]
                home = self.home.get(path)
                if home is not None and path in self.ops:
                    self.ops[path].Set(Gf.Vec3d(want[0] - home[0], want[1] - home[1], 0.0))
