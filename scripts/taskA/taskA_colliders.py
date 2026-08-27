# 배포용 정본 -- 대회 환경 저장소 `Task-A/sim/store_colliders.py` 에서 그대로 옮겼다.
# 한 줄도 고치지 않았다. 배포 이미지에는 `Task-A/` 가 없으므로 참가자 데모가 읽을 수 있는
# 자리로 옮겼을 뿐이다. 아래는 원본의 기록 그대로다.
#
# 이 파일이 없으면 안 되는 이유는 콜라이더다: 구워진 매장에서 벽·시식 탁상·스툴은 콜라이더가
# 없고, 바닥의 CollisionAPI 는 꺼진 채로 실려 온다. 켜지 않으면 로봇은 z = -3.563 까지
# 떨어지고 바구니는 탁상을 뚫고 지나간다.
# ---------------------------------------------------------------------------------------------

# Copyright 2025.
#
# Give every fixture in the baked store a collider, at load time.
#
# WHY THIS IS NEEDED AT ALL
#   Only three things in the baked store arrive without colliders, and the robot passes through
#   all three: the walls (plain Cubes), the eat-in tables and stools (visual references), and the
#   floor, whose one CollisionAPI prim ships authored but DISABLED -- without it the robot falls
#   to z = -3.563.
#
#   THE FLOOR IS SWITCHED ON AND LEFT AS THE ASSET AUTHORED IT -- `sdf` -- by the user's
#   decision on 2026-08-17, after the measurements below were in hand. Raising the physics rate
#   to 120 Hz makes the carry succeed on this floor anyway (arrived 0.062 m short, crate held),
#   so the floor is no longer the thing standing between us and a demonstration. `convexHull`
#   remains selectable and remains the smoother of the two if that changes.
#
#   THE MEASUREMENT THAT PROMPTED IT, kept because it is still true. It
#   ships as `sdf` at the default resolution, which is 48 mm of sampling across a 10 mm slab, and
#   a robot rolling on the surface that reconstructs from is a robot that rattles hard enough to
#   drop what it carries. The measurements and the arithmetic are at the `name == "Floor"` branch
#   below. A convex hull of a flat plate is that plate exactly, so the store keeps colliding with
#   the floor it draws.
#
#   Everything else is already solid, and this file exists partly to record how that was got
#   wrong. Reading the export's per-fixture collider count, twelve fixtures showed zero and were
#   reported -- twice -- as things the robot would drive through, the checkout among them. They
#   were not. Those fixtures keep their colliders on separate `collisions/` meshes rather than on
#   the visible `visuals/` ones, and the export's footprint pass never counted them. The gondolas
#   carry theirs on the visible mesh, which is why some counted and some did not.
#
#   The lesson is in the prim path, so it is written down here: a fixture with
#   `.../Body_link/collisions/Body_link_col_0` is solid. Counting geometry is not the same as
#   asking what collides.
#
# WHY IT LIVES HERE
#   Three scripts had their own copy of this, each hardening a slightly different set: walls,
#   eat-in furniture and the floor, and nothing else. That was not a decision, it was the point at
#   which the visible symptom stopped -- the robot fell through the floor without the floor, and
#   through the cafe tables without the tables. One copy, covering everything, cannot drift.
#
# WHY IT IS DONE AT LOAD TIME AND NOT BAKED
#   store_scene.usd is a committed, shared artefact that other people's work reads. Regenerating
#   it to add colliders is the better fix and is not ours to make unilaterally.

from pxr import Usd, UsdPhysics

STORE_PATH = "/World/envs/env_0/Store"

_SOLID_TYPES = ("Mesh", "Cube", "Cylinder", "Sphere", "Capsule", "Cone")


def _enable(prim):
    api = (UsdPhysics.CollisionAPI.Apply(prim) if not prim.HasAPI(UsdPhysics.CollisionAPI)
           else UsdPhysics.CollisionAPI(prim))
    (api.GetCollisionEnabledAttr() or api.CreateCollisionEnabledAttr()).Set(True)


def _has_enabled_collider(prim) -> bool:
    """Does anything with actual GEOMETRY under here collide?

    Geometry only, on purpose. Asking "does any prim carry an enabled CollisionAPI" reported 25 of
    29 fixtures as already solid and left the twelve the whole exercise was about untouched --
    the fridges and the checkout carry the API on their `Body_link` xforms, which have no points
    for PhysX to collide with. The export counts geometry prims and this has to match it, or the
    two disagree about the same store.
    """
    return bool(_enabled_geometry(prim))


def _enabled_geometry(prim) -> list:
    """Paths of the geometry prims under `prim` that actually collide."""
    out = []
    for p in Usd.PrimRange(prim):
        if p.GetTypeName() not in _SOLID_TYPES:
            continue
        if p.HasAPI(UsdPhysics.CollisionAPI):
            attr = UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr()
            if attr and attr.Get():
                out.append(str(p.GetPath()))
    return out


def harden(stage, log=print, store_path: str = STORE_PATH,
           floor_approx: str = "sdf") -> dict:
    """Turn every fixture solid. Returns what was done, per fixture, for the caller to print.

    The floor's own CollisionAPI prim ships authored-but-disabled, and without it the robot falls
    to z = -3.563. The walls are plain Cubes. The eat-in sets are visual references. None of that
    raises anything -- the robot simply passes through.

    Convex hulls, not the triangle meshes as authored: a hull is legal on any body and cheap, and
    nothing here needs a shelf's exact concavity. The fridge doors become part of the solid body
    rather than staying hinged, which this scene does not care about and a manipulation scene
    would.
    """
    store = stage.GetPrimAtPath(store_path)
    if not store or not store.IsValid():
        log(f"harden: {store_path} 없음")
        return {}

    report = {"already": [], "added": [], "floor": 0, "floor_skipped": False}
    for child in store.GetChildren():
        name = child.GetName()

        if name == "Floor" and floor_approx == "off":
            # 바닥 콜라이더를 켜지 않고 그대로 둔다 -> 출하 상태(authored-but-DISABLED)로 남고,
            # 로봇은 GroundPlane 을 탄다.  이 파일 첫머리가 적어둔 "지면판만" 조건이 그것이다.
            #
            # `"none"` 으로는 이걸 못 한다 -- 그것은 USD 의 approximation 토큰이고 "근사하지
            # 않음 = 삼각형 메시로 충돌" 이라는 뜻이라, 콜라이더는 여전히 켜진다.
            #
            # report["floor_skipped"] 는 이 파일이 처음부터 자리를 비워 둔 필드였고 아무도
            # True 로 만들지 않았다.  이제 여기서 채운다.
            report["floor_skipped"] = True
            report["floor_approx"] = "off"
            log("harden: 바닥 콜라이더를 켜지 않는다 (지면판만 탄다)")
            continue

        if name == "Floor":
            # THE FLOOR IS SWITCHED ON AND KEEPS THE APPROXIMATION IT SHIPS WITH, `sdf`. The
            # user's requirement is that the collider be configured at all, and it is; which
            # approximation it uses is left where the asset put it.
            #
            # `floor_approx` exists so that can be revisited without editing anything, because
            # the measurement below says the shipped one is the rougher of the two -- and 120 Hz
            # is what currently makes that survivable rather than the floor being right.
            #
            # WHAT THE MEASUREMENT SAID. 2026-08-17 (Task-A/sim/floor_audit.py --stage roll,
            # vx = 0.25, runs differing only in which floors were live):
            #
            #     floors present          wheel ripple   wheel step   wheel height error
            #     store floor (sdf) + plane  6.97 mm      2.76 mm       -1.71 mm
            #     GroundPlane only           4.68 mm      0.78 mm       -1.54 mm
            #
            # and a whole carry, same plan, same machine, differing only in that:
            #
            #     store floor (sdf) + plane  crate sank 345 mm and was dropped, 9.27 m short
            #     GroundPlane only           arrived holding the crate, 0.077 m short
            #
            # WHY, and it is NOT that a mesh is bumpier than a plane -- a triangulated flat slab
            # is still exactly flat. It is the approximation. The floor is 12.4 x 12.37 m and
            # 10 mm THICK, and `sdf` with no authored resolution takes the default 256 samples
            # across the longest axis:
            #
            #     12.4 m / 256 = 48 mm per sample,  against a 10 mm slab
            #
            # The slab is thinner than one sample of the field meant to describe it, so the
            # surface PhysX reconstructs is not the surface that was authored. That is where the
            # roughness comes from, and it is why the wheels sat 1.7-2.1 mm off their own radius.
            #
            # A convex hull of a rectangular plate is that plate -- analytically flat, no
            # sampling anywhere -- which is why it is the alternative on offer. Either way the
            # store collides with its OWN floor rather than leaning on the infinite ground plane:
            # the plane does not stop where the building does.
            #
            # carry_scene.py:129 says the store floor and the plane "coincide exactly rather than
            # fighting". They are 2 mm apart (floor top +0.002, plane 0, VISIBLE floor +0.000245)
            # and the robot was riding the higher, broken one. Both halves of that sentence were
            # wrong, and neither had been measured.
            n = 0
            for p in Usd.PrimRange(child):
                if not p.HasAPI(UsdPhysics.CollisionAPI):
                    continue
                _enable(p)
                if p.GetTypeName() == "Mesh":
                    api = (UsdPhysics.MeshCollisionAPI(p)
                           if p.HasAPI(UsdPhysics.MeshCollisionAPI)
                           else UsdPhysics.MeshCollisionAPI.Apply(p))
                    (api.GetApproximationAttr() or api.CreateApproximationAttr()).Set(floor_approx)
                n += 1
            report["floor"] = n
            report["floor_approx"] = floor_approx
            log(f"harden: 바닥 콜라이더 {n}개, 근사 {floor_approx}")
            continue

        enabled = _enabled_geometry(child)
        if enabled:
            report["already"].append((name, len(enabled), enabled[0]))
            continue

        n = 0
        for p in Usd.PrimRange(child):
            if p.GetTypeName() not in _SOLID_TYPES:
                continue
            _enable(p)
            if p.GetTypeName() == "Mesh":
                UsdPhysics.MeshCollisionAPI.Apply(p).CreateApproximationAttr().Set(
                    UsdPhysics.Tokens.convexHull)
            n += 1
        if n:
            report["added"].append((name, n))

    log(f"harden: 이미 있던 기물 {len(report['already'])}개, "
        f"새로 켠 기물 {len(report['added'])}개, 바닥 {report['floor']}개")
    for name, n in report["added"]:
        log(f"   + {name} ({n}개 형상)")
    for name, n, first in report["already"]:
        log(f"   = {name}: 형상 콜라이더 {n}개, 예: {first.split('/', 6)[-1]}")
    return report
