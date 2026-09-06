"""Task-C 채점용 기하 — 해석적 최근접점·AABB·띠 교차.

평가안 규정:
  - 상품을 **원통 또는 박스로 근사**해 빔 출발선까지의 최근접 거리를 해석적으로 푼다.
  - 메시 최근접점 질의는 쓰지 않는다 (8종 전부 원통·직육면체라 근사 오차가 mm 단위).

쿼터니언은 이 저장소 규약대로 **(w, x, y, z)** 를 쓴다.
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "quat_to_mat", "obb_corners", "aabb_from_obb",
    "closest_dist_cylinder", "closest_dist_box", "closest_dist",
    "obb_sample_points", "aabb_xy_overlaps_rect",
]


def quat_to_mat(q) -> np.ndarray:
    """(w,x,y,z) -> 3x3 회전행렬."""
    w, x, y, z = (float(v) for v in q)
    n = math.sqrt(w * w + x * x + y * y + z * z)
    if n < 1e-12:
        return np.eye(3)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=float)


def obb_corners(center, quat, half_extents) -> np.ndarray:
    """OBB 8 꼭짓점 (월드)."""
    R = quat_to_mat(quat)
    c = np.asarray(center, dtype=float)
    he = np.asarray(half_extents, dtype=float)
    out = []
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                out.append(c + R @ (np.array([sx, sy, sz]) * he))
    return np.asarray(out)


def aabb_from_obb(center, quat, half_extents):
    """OBB 를 감싸는 월드 축정렬 AABB -> (min3, max3).

    상판 대비 높이·낙하 판정·띠 교차가 전부 이 AABB 기준이다(평가안 규정).
    """
    P = obb_corners(center, quat, half_extents)
    return P.min(axis=0), P.max(axis=0)


def closest_dist_cylinder(p, center, axis, radius, half_height) -> float:
    """외부 점 p 에서 **원통 표면**까지의 최단 거리. 내부면 0.0.

    옆면·바닥면·테두리(rim) 세 경우를 나눠 해석적으로 푼다.
    """
    p = np.asarray(p, dtype=float)
    c = np.asarray(center, dtype=float)
    a = np.asarray(axis, dtype=float)
    n = np.linalg.norm(a)
    if n < 1e-12:
        raise ValueError("cylinder axis is degenerate")
    a = a / n
    v = p - c
    ax = float(np.dot(v, a))              # 축방향 성분
    rad = float(np.linalg.norm(v - ax * a))   # 반경방향 거리
    dz = abs(ax) - float(half_height)     # 캡 밖으로 나간 양
    dr = rad - float(radius)              # 옆면 밖으로 나간 양
    if dz <= 0.0 and dr <= 0.0:
        return 0.0                        # 내부
    if dz <= 0.0:
        return dr                         # 옆면
    if dr <= 0.0:
        return dz                         # 캡
    return math.hypot(dz, dr)             # 테두리


def closest_dist_box(p, center, quat, half_extents) -> float:
    """외부 점 p 에서 **OBB 표면**까지의 최단 거리. 내부면 0.0."""
    R = quat_to_mat(quat)
    c = np.asarray(center, dtype=float)
    he = np.asarray(half_extents, dtype=float)
    local = R.T @ (np.asarray(p, dtype=float) - c)
    d = np.abs(local) - he
    outside = np.maximum(d, 0.0)
    return float(np.linalg.norm(outside))   # 내부면 전부 0 -> 0.0


def closest_dist(p, prod) -> float:
    """상품 근사 형상에 따라 최근접 거리를 고른다.

    prod 는 최소한 다음을 갖는다:
      shape: "cylinder" | "box"
      pos, quat, half_extents            (box)
      pos, quat, radius, half_height, axis_local   (cylinder)
    """
    if prod["shape"] == "cylinder":
        R = quat_to_mat(prod["quat"])
        axis_world = R @ np.asarray(prod.get("axis_local", (0.0, 0.0, 1.0)), dtype=float)
        return closest_dist_cylinder(p, prod["pos"], axis_world,
                                     prod["radius"], prod["half_height"])
    return closest_dist_box(p, prod["pos"], prod["quat"], prod["half_extents"])


def obb_sample_points(center, quat, half_extents, ref) -> np.ndarray:
    """평가안의 샘플점 9개 = OBB **면 중심 6 + ref 에 가장 가까운 꼭짓점 3**."""
    R = quat_to_mat(quat)
    c = np.asarray(center, dtype=float)
    he = np.asarray(half_extents, dtype=float)
    faces = []
    for ax in range(3):
        for s in (-1.0, 1.0):
            off = np.zeros(3)
            off[ax] = s * he[ax]
            faces.append(c + R @ off)
    corners = obb_corners(center, quat, half_extents)
    order = np.argsort(np.linalg.norm(corners - np.asarray(ref, dtype=float), axis=1))
    return np.vstack([np.asarray(faces), corners[order[:3]]])


def aabb_xy_overlaps_rect(aabb_min, aabb_max, rect) -> bool:
    """AABB 의 XY 투영이 사각 띠(x0,x1,y0,y1)와 **일부라도** 겹치는가.

    평가안: 중심이 아니라 AABB 교차로 본다. 중심 기준이면 「걸침 허용」이 성립하지 않는다.
    """
    x0, x1, y0, y1 = (float(v) for v in rect)
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    return not (aabb_max[0] < x0 or aabb_min[0] > x1
                or aabb_max[1] < y0 or aabb_min[1] > y1)
