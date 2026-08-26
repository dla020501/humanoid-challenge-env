"""과제 B 상품 skin USD 의 텍스처 참조를 자기 폴더의 상대경로로 다시 쓴다 (stage 안에서).

상품 skin USD 가 색 텍스처를 개발 머신의 **절대경로**로 물고 있으면, 바로 옆에 같은
그림이 있어도 그쪽을 보지 않는다 -- 텍스처가 빠진 채 평가 두 판을 돌리고 나서야
발견된 함정이다 (2026-08-25 이전 파이프라인의 기록). 이 스크립트는 stage 로 추려진
사본의 그 경로들을 `./textures/<이름>` 상대경로로 바꿔 써서, 상품 폴더 하나만 있으면
색이 따라오게 만든다. 이미 상대경로라면 같은 값으로 다시 쓸 뿐이라 해가 없다.

에셋 재배치는 하지 않는다 -- 과제 B 씬이 매장 전체를 스폰하게 되면서(2026-08-25)
convstore 트리를 원본 경로 그대로 배포하므로, 옮길 것도 경로 상수를 고칠 것도 없다.

pxr 은 Isaac Sim 을 띄우지 않고도 쓸 수 있다 -- build_image.sh 가 그렇게 부른다.
"""

import json
import os
import shutil
import sys

from pxr import Sdf

STAGE = sys.argv[1]
PRODUCTS_DIR = f"{STAGE}/source/cyclo_lab/data/props/convstore/taskB_products"


def texture_specs(layer):
    """이 레이어가 물고 있는 그림 파일 속성 전부. [(AttributeSpec, 원래 경로)].

    합성된 Stage 가 아니라 **레이어 자체**를 연다. 고쳐야 하는 것은 파일에 적힌 값이고,
    Stage 로 열면 참조가 합성돼 어느 파일에 쓸지가 흐려진다.
    """
    out = []

    def walk(spec):
        for attr in spec.properties:
            if not isinstance(attr, Sdf.AttributeSpec):
                continue
            if attr.typeName != Sdf.ValueTypeNames.Asset:
                continue
            value = attr.default
            if value is None or not value.path:
                continue
            # MDL 자체(`OmniPBR.mdl`)는 Isaac 이 자기 경로에서 찾는다. 건드리면 재질이 죽는다.
            if value.path.endswith(".mdl"):
                continue
            out.append((attr, value.path))
        for child in spec.nameChildren:
            walk(child)

    walk(layer.pseudoRoot)
    return out


def retexture(product_dir, skin_usd):
    """상품 하나의 텍스처 참조를 ./textures/<이름> 으로 다시 쓴다. 고친 곳 수를 돌려준다.

    파일 하나하나를 대응시킨다 -- 색 지도는 albedo.png 라는 이름을 갖고, 그 밖의 맵이
    있으면 원래 파일 이름을 그대로 쓴다. 원래 그림이 상품 폴더에 없으면 실패한다.
    """
    layer = Sdf.Layer.FindOrOpen(skin_usd)
    if layer is None:
        raise RuntimeError(f"열 수 없다: {skin_usd}")

    renamed = {}
    for _attr, raw in texture_specs(layer):
        if raw in renamed:
            continue
        base = os.path.basename(raw)
        renamed[raw] = "albedo.png" if base == "material_0.png" else base

    changed = 0
    for attr, raw in texture_specs(layer):
        new_name = renamed[raw]
        source = os.path.join(product_dir, "textures", os.path.basename(raw))
        if not os.path.isfile(source):
            raise RuntimeError(
                f"{skin_usd} 가 {raw} 를 물고 있는데 그 그림이 상품 폴더에 없다: {source}")
        dst = os.path.join(product_dir, "textures", new_name)
        if os.path.abspath(source) != os.path.abspath(dst):
            shutil.copy2(source, dst)
        attr.default = Sdf.AssetPath(f"./textures/{new_name}")
        changed += 1

    if not changed:
        raise RuntimeError(f"{skin_usd} 에 고칠 텍스처 경로가 없다 -- "
                           f"에셋 구조가 바뀌었다면 이 스크립트를 다시 재야 한다.")
    layer.Save()
    return changed


def main():
    with open(f"{PRODUCTS_DIR}/manifest.json", encoding="utf-8") as fh:
        products = json.load(fh)["products"]
    total = 0
    for name in sorted(products):
        total += retexture(f"{PRODUCTS_DIR}/{name}", f"{PRODUCTS_DIR}/{name}/{name}_skin.usd")
    print(f"[retexture] 상품 {len(products)} 개, 텍스처 경로 {total} 곳을 상대경로로 다시 썼다")


main()
