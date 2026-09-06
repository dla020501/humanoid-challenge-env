# Copyright 2025.
#
# Where the fingers are relative to the crate, in the crate's own frame.
#
# WHY THIS IS A FILE OF ITS OWN
#   The competition scorer must not import anything that knows how the grasp was produced. This
#   module takes positions and quaternions and returns numbers; it has never heard of cuRobo, of
#   `reach_rim.npz`, or of a policy. `docs/convstore/GRASP_VERDICT.md` names that as its second
#   rule -- judge on the outcome, never the process -- after four verdicts in one day got it wrong.
#
# THIS ARITHMETIC ALSO EXISTS IN `Task-A/curobo/grasp_test.py:325-381`.
#   It is copied, not shared, because the instruction for this work is that no existing file may be
#   edited. That is the duplication `Task-A/CLAUDE.md` 4 and 13 warn about three times over, so two
#   things guard it:
#     * this notice, naming the other copy, so whoever changes one goes and looks at the other
#     * a live cross-check: run `grasp_test.py --which N` and the scorer on the same plan and
#       compare `gap_mm` / `straddle` / `centre_off_mm`. They are tied by measurement, not by code.
#   If the two ever disagree, the one that was measured against a human label wins.
#
# WHAT IS DELIBERATELY DIFFERENT FROM THAT COPY
#   `grasp_test.py:336` decides which wall a hand should hold from WHICH HAND IT IS -- left holds
#   the -y wall, right holds +y. That is true of our grasps and of nothing else. A contestant is
#   free to come at the crate the other way round, and would be scored zero for holding it
#   perfectly. Here a hand is asked only whether it has A wall between its fingers, and the pair is
#   asked whether those two walls are OPPOSITE ones.

import math

import numpy as np

# THE CRATE. Values are `rim_targets.CRATE`'s, restated here so this module has no imports beyond
# numpy. The crate has not changed since it was measured (Task-A/CLAUDE.md 47 re-checked it when
# the store furniture was replaced: the table top moved 6.1 mm, the crate did not move at all).
CRATE_ALONG = 0.380          # x in the crate's own frame
CRATE_ACROSS = 0.590         # y -- the two long walls the hands grip
CRATE_HEIGHT = 0.140         # z. The origin is the UNDERSIDE, so this is also the rim's top edge
WALL_T = 0.017               # what the fingers actually close on

CRATE_ACROSS_HALF = CRATE_ACROSS / 2.0
RIM_PLANE = CRATE_ACROSS_HALF - WALL_T / 2.0     # mid-plane of a wall, in crate coordinates
RIM_TOP = CRATE_HEIGHT


def qconj(q):
    """(w,x,y,z) -> its conjugate."""
    return np.array([q[0], -q[1], -q[2], -q[3]], dtype=np.float64)


def qapply(q, v):
    """Rotate v by the quaternion q, both in (w,x,y,z) / (x,y,z) order."""
    w, x, y, z = (float(c) for c in q)
    v = np.asarray(v, dtype=np.float64)
    t = 2.0 * np.cross((x, y, z), v)
    return v + w * t + np.cross((x, y, z), t)


def crate_axes(crate_quat):
    """The crate's own along / across / up axes, expressed in world."""
    return (qapply(crate_quat, (1.0, 0.0, 0.0)),
            qapply(crate_quat, (0.0, 1.0, 0.0)),
            qapply(crate_quat, (0.0, 0.0, 1.0)))


def hand_report(tip_a, tip_b, crate_pos, crate_quat):
    """One hand against the crate. Which wall it has hold of, if any, and how well.

    `tip_a` / `tip_b` are the two fingertip positions in world; the caller says which bodies those
    are. Returns millimetres throughout, and `wall` is +1 / -1 / None -- the sign of the wall the
    fingers straddle, in the crate's own across axis, or None for neither.

    A hand can only straddle one wall: the jaw opens to about 107 mm and the walls are 573 mm
    apart. The loop below still checks both and takes the nearer, so nothing depends on that.
    """
    p = np.asarray(crate_pos, dtype=np.float64)
    along_ax, across, up = crate_axes(crate_quat)
    a = np.asarray(tip_a, dtype=np.float64)
    b = np.asarray(tip_b, dtype=np.float64)

    # Signed distance of each fingertip from each candidate wall's mid-plane, along the across
    # axis. Straddling means the two tips land on opposite sides of it.
    cands = []
    for sign in (+1.0, -1.0):
        wall = sign * RIM_PLANE
        da = float(np.dot(a - p, across)) - wall
        db = float(np.dot(b - p, across)) - wall
        cands.append({"wall": int(sign), "tip_a_mm": da * 1000.0, "tip_b_mm": db * 1000.0,
                      "straddle": (da > 0.0) != (db > 0.0),
                      "centre_off_mm": (da + db) / 2.0 * 1000.0})
    # A STRADDLED WALL WINS OVER A NEAR ONE. Sorting by distance alone would let a hand that is
    # holding the far wall be reported against the near one, which reads as "not straddling".
    # Among equals, the nearer plane -- that is the tie-break, not the test.
    held = [c for c in cands if c["straddle"]]
    best = min(held or cands, key=lambda c: abs(c["centre_off_mm"]))
    if not best["straddle"]:
        best = dict(best, wall=None)

    # HOW DEEP THE HAND IS. Nothing measured this until 2026-08-16, when the user watched three
    # takes where a hand failed to hold and said it looked too LOW -- pushing the crate rather than
    # gripping it. `centre_off_mm` cannot see that: it is measured ACROSS the wall, and a hand can
    # be perfectly centred on the wall plane while sitting 40 mm below the rim. Zero means the
    # fingertips are level with the rim's top edge; negative is below it, where the wall is.
    ha = float(np.dot(a - p, up)) - RIM_TOP
    hb = float(np.dot(b - p, up)) - RIM_TOP
    al = (float(np.dot(a - p, along_ax)) + float(np.dot(b - p, along_ax))) / 2.0

    best.update({"gap_mm": float(np.linalg.norm(a - b)) * 1000.0,
                 "depth_mm": (ha + hb) / 2.0 * 1000.0,
                 "along_mm": al * 1000.0})

    # THE WALL IS A RECTANGLE, NOT AN INFINITE PLANE.
    #
    # `straddle` above is a sign test against a plane, and a plane has no edges: a hand held out
    # across the room lands on one side of it, the other hand on the other, and the pair reads as
    # holding the crate. That is not hypothetical -- the first run of this scorer gave a robot
    # that had not moved at all a hand "on the wall", because its folded arm happened to sit
    # across the extended plane 0.7 m from the crate.
    #
    # `grasp_test.py:330` carries the same sign test and is never wrong about it, because it is
    # only ever called at a pose that was planned to be at the rim. A competition scorer gets
    # whatever the contestant does, so the fingers have to be shown to be ON the wall: within the
    # crate's own length, and between its floor and its rim. The margin is one wall thickness --
    # a dimension of the crate, not a tolerance picked to make some run pass.
    on_wall = (abs(al) <= CRATE_ALONG / 2.0 + WALL_T
               and -CRATE_HEIGHT - WALL_T <= (ha + hb) / 2.0 <= WALL_T)
    best["on_wall_extent"] = bool(on_wall)
    if not on_wall:
        best["straddle"] = False
        best["wall"] = None
    return best


def opposite_walls(left, right):
    """Do these two hands hold DIFFERENT walls? Both on one wall is not a two-sided grasp."""
    return (left.get("wall") is not None and right.get("wall") is not None
            and left["wall"] != right["wall"])


def in_wrist(crate_pos, wrist_pos, wrist_quat):
    """The crate's centre in that wrist's own frame, metres.

    WHY THE WRIST FRAME. In world coordinates "the arm sagged" and "the crate slid through the
    jaws" look identical -- both are the crate getting lower. Referred to the wrist, the arm's
    rigid motion cancels and what is left is only how far the crate moved with respect to the
    hand. Task B measures exactly this (`task_b_episode.py:2446`); the same arithmetic is in
    `Task-A/automation/collector/carry_episode.py:930`.
    """
    p = np.asarray(wrist_pos, dtype=np.float64)
    return qapply(qconj(wrist_quat), np.asarray(crate_pos, dtype=np.float64) - p)


def tilt_deg(crate_quat):
    """Angle between the crate's own up axis and world up. Not scored -- reported."""
    up = qapply(crate_quat, (0.0, 0.0, 1.0))
    return math.degrees(math.acos(max(-1.0, min(1.0, float(up[2])))))
