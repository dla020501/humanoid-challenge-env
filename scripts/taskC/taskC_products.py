# Copyright 2026.
#
# 과제 C 의 상품 8 종. 코드용 이름이 폴더·USD·타일 json 의 키이고, 영어 이름은 지시문과
# 장면 JSON 의 `label` 에 들어간다 (과제 B 와 같은 두 이름 규칙).
#
# 상품 하나에 필요한 것은 넷이고 전부 코드용 이름 하나로 이어진다.
#
#   products_c/<이름>/<이름>_phys.usd   QR 타일이 붙은 물리 USD (스폰되는 것)
#   products_c/<이름>/info.json         치수(mm) 등 -- 배치가 반치수를 여기서 잰다
#   products_c/_qr_tiles.json           타일 중심·법선 (상품 프레임) -- QR 면을 조준할 때 쓴다
#   products_c/_qr_tiles_vis.json       (있으면) 렌더 실측으로 보정한 QR 방위 -- 없으면 타일 법선
#
# 에셋은 배포 이미지에서 온다 -- 코드는 `source/cyclo_lab/data/products_c` 를 본다. 개발
# 체크아웃(대회 환경 저장소)에서는 같은 파일이 `taskC/out/qr_usd` 에 있으므로 그쪽도 본다.
# `TASKC_ASSETS` 는 테스트가 작업 폴더의 사본을 가리키게 할 때만 쓴다.
#
# isaaclab 을 쓰지 않는 순수 파이썬이다. 데모 스크립트가 AppLauncher 보다 먼저 이 모듈을
# 읽는데, isaaclab 이 SimulationApp 보다 먼저 import 되면 Isaac Sim 이 아예 뜨지 않는다.

import json as _json
import os as _os
import pathlib as _pathlib

# 코드용 이름 -> 영어 이름, 원통 여부. 원통 여부는 원본 kit_config.is_cylindrical 의 판정을
# 그대로 옮긴 것이다(이름 패턴). 예감은 실측 8각기둥 상자(oct8)라 원통이 아니다.
PRODUCTS = {
    "pringles_original_small":  {"label": "small original Pringles tube",    "cyl": True},
    "pringles_sourcream_small": {"label": "small sour cream Pringles tube",  "cyl": True},
    "ottogi_cupnoodle_buldak":  {"label": "Ottogi Buldak cup noodle",        "cyl": True},
    "yegam_original":           {"label": "Yegam original potato chip tube", "cyl": False},
    "samyang_buldak_cup":       {"label": "Buldak stir-fried noodle cup",    "cyl": True},
    "chilsung_cider":           {"label": "Chilsung cider can",              "cyl": True},
    "cocacola_zero":            {"label": "Coca-Cola zero can",              "cyl": True},
    "lotte_sand":               {"label": "Lotte Sand biscuit box",          "cyl": False},
}
LABELS = {k: v["label"] for k, v in PRODUCTS.items()}

_CYCLOLAB = _os.environ.get("CYCLOLAB_PATH", "/workspace/cyclo_lab")
_IMAGE_DATA = f"{_CYCLOLAB}/source/cyclo_lab/data"


def assets_root() -> _pathlib.Path:
    """에셋 뿌리. 우선순위: TASKC_ASSETS > 이미지(data/) > 개발 체크아웃(taskC/out)."""
    env = _os.environ.get("TASKC_ASSETS")
    if env:
        return _pathlib.Path(env)
    if _os.path.isdir(f"{_IMAGE_DATA}/products_c"):
        return _pathlib.Path(_IMAGE_DATA)
    return _pathlib.Path(_IMAGE_DATA)


def products_dir() -> _pathlib.Path:
    """상품 8 종이 들어 있는 폴더. 이미지에서는 data/products_c, 개발 체크아웃에서는 taskC/out/qr_usd."""
    a = assets_root() / "products_c"
    if a.is_dir():
        return a
    dev = _pathlib.Path(_CYCLOLAB) / "taskC" / "out" / "qr_usd"
    return dev if dev.is_dir() else a


def product_dir(slug: str) -> _pathlib.Path:
    return products_dir() / slug


def product_usd(slug: str) -> _pathlib.Path:
    return product_dir(slug) / f"{slug}_phys.usd"


# 평가 표본 시드. `--seed 0/1/2` 는 cstore-challenge `ship/ground_truth_sample/` 의 세 판(상품 3개
# 연속 정답 궤적)을 가리킨다. 그 장면은 원 시드(SAMPLE_SEEDS 값)로 만들었지만 상품 조합은 수집
# 파이프라인이 따로 정한 것이라 시드만으로 되살릴 수 없다. 그래서 정착된 장면 파일을 `samples/` 에
# 그대로 두고, 표본 시드를 받으면 딜하지 않고 그 파일을 세운다 -- 정답 궤적과 mm 까지 같은 자리다.
SAMPLE_SEEDS = {0: 3015066000, 1: 3050039000, 2: 4156003000}
_SAMPLES = _pathlib.Path(__file__).resolve().parent / "samples"


def resolve_seed(seed) -> int:
    """표본 시드(0·1·2)면 원 시드로, 아니면 그대로."""
    return int(SAMPLE_SEEDS.get(int(seed), int(seed)))


def sample_scene_path(seed):
    """표본 시드면 그 장면 파일 경로, 아니면 None."""
    if int(seed) in SAMPLE_SEEDS:
        f = _SAMPLES / f"scene_{int(seed)}.json"
        if f.is_file():
            return f
    return None


def scanner_usd() -> _pathlib.Path:
    """스캐너 USD. 이미지에서는 data/fixtures/scanner/, 개발 체크아웃에서는 props/convstore/fixtures/scanner_taskC/."""
    cands = (assets_root() / "fixtures" / "scanner" / "scanner_taskC.usd",
             _pathlib.Path(_CYCLOLAB) / "source" / "cyclo_lab" / "data" / "props" / "convstore"
             / "fixtures" / "scanner_taskC" / "scanner_taskC.usd")
    for c in cands:
        if c.is_file():
            return c
    return cands[0]


def store_usd() -> _pathlib.Path:
    """매장 USD. 이미지에서는 data/store/scene/fixture_kit/out/, 개발 체크아웃에서는 fixture_kit/out/."""
    cands = (assets_root() / "store" / "scene" / "fixture_kit" / "out" / "store_scene.usd",
             _pathlib.Path(_CYCLOLAB) / "fixture_kit" / "out" / "store_scene.usd")
    for c in cands:
        if c.is_file():
            return c
    return cands[0]


def size_mm(slug: str):
    """(x, y, z) mm -- info.json 의 size. 상품 프레임 축 순서 그대로다."""
    with open(product_dir(slug) / "info.json", encoding="utf-8") as fh:
        return tuple(float(v) for v in _json.load(fh)["size"])


_TILES = None


def _tiles():
    global _TILES
    if _TILES is None:
        with open(products_dir() / "_qr_tiles.json", encoding="utf-8") as fh:
            _TILES = _json.load(fh)
    return _TILES


def tile_normal(slug: str):
    """QR 타일 법선 (상품 프레임, 단위 벡터)."""
    return tuple(float(v) for v in _tiles()[slug]["normal"])


def optional_json(name: str) -> dict:
    """products_c 안의 선택 파일(`_qr_tiles_vis.json`, `_spawn_faces.json`). 없으면 빈 dict."""
    p = products_dir() / name
    if not p.is_file():
        return {}
    with open(p, encoding="utf-8") as fh:
        return _json.load(fh)


def is_cylinder(slug: str) -> bool:
    return PRODUCTS[slug]["cyl"]
