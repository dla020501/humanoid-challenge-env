# 환경 에셋 (Assets) 구조

> [← 메인 README 로 돌아가기](../README.md)

시뮬레이션 구동에 필수적인 에셋은 도커 이미지 내 `/workspace/assets` 경로에 위치하며, 소스 코드에서는 `source/cyclo_lab/data` 심볼릭 링크를 통해 참조합니다. 이 디렉토리에는 **Task A·B·C** 실행에 필요한 필수 파일만 경량화되어 탑재되어 있습니다.

```text
data/
  ├── robot/                 # 로봇 에셋 (40 MB)
  │   └── ffw_sg2.usd          # 로봇 원본 USD
  │
  ├── fixtures/              # 매장 집기 에셋 (456 KB)
  │   ├── shelf/shelf.usd      # 진열대 (재질 이미지 4장 포함)
  │   ├── table/table.usd      # 목적지 옆 책상
  │   ├── crate/crate.usd      # 파란 상자
  │   └── scanner/scanner_taskC.usd  # 과제 C 바코드 스캐너
  │
  ├── products/              # 과제 B 목표 상품 36종 (196 MB)
  │   ├── manifest.json        # 상품별 크기, 무게, 콜라이더, 참조 USD 정보
  │   ├── orientation.json     # 상품별 상단(Up-face) 축 정의
  │   ├── display_yaw.json     # 진열 시 기본 회전 각도(Yaw) 정의
  │   ├── shapes.json          # 형태(상자형/원통형) 구분 및 상자 내 초기 배치 형태 정의
  │   └── cocacola_zero/       # 개별 상품 디렉토리 예시 (총 36종)
  │       ├── cocacola_zero.usd       # 시뮬레이션에 생성(Spawn)되는 최상위 USD
  │       ├── cocacola_zero_skin.usd  # 시각적 메시(Mesh) 및 재질(Material) 구조
  │       └── textures/albedo.png     # 텍스처 이미지 파일
  │
  ├── products_c/            # 과제 C 목표 상품 8종 (39 MB) — QR 타일 부착본
  │   ├── products.json        # 이름, 가격, QR 타일 부착 위치 데이터
  │   ├── _qr_tiles.json       # 타일의 법선 벡터 및 스케일
  │   ├── taskC_products.json  # 크기 및 콜라이더 수치
  │   ├── taskC_barcodes.json  # QR 면의 3D 공간상 꼭짓점 좌표
  │   └── cocacola_zero/       # 개별 상품 디렉토리 예시 (총 8종)
  │       ├── cocacola_zero_phys.usd  # 스폰 대상 최상위 물리 USD (동일 폴더 .usdc/텍스처 상대 참조)
  │       ├── cocacola_zero.usdc      # 메시 및 재질
  │       └── cocacola_zero.png       # 텍스처 이미지 파일
  │
  └── store/                 # 과제 A 매장 환경 에셋 (184 MB)
      ├── manifest.json        # 매장 내 진열대/냉장고 20종 및 배치 상품 35종 메타데이터
      ├── layout.json          # 매장 전체 레이아웃 좌표 데이터
      └── scene/               # 과제 A 시뮬레이션용 매장 전체 3D 씬 (USD)
          ├── fixture_kit/out/store_scene.usd  # 매장 전체 씬의 최상위(Root) 파일
          ├── fixture_kit/<킷>/assets/...      # 곤돌라, 냉동고, 와인, 시식 코너 파츠 등
          └── source/cyclo_lab/data/props/...  # 쇼케이스, 계산대 등 단일 집기 에셋
```
