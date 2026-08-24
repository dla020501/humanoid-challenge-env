#!/bin/bash
# 컨테이너가 처음 하는 일.
#
# 두 가지를 하고 넘긴다.
#
# 1. `_isaac_sim` 심볼릭 링크를 다시 건다. 빌드 때 걸어 두지만 볼륨이 그 자리를
#    덮으면 사라지므로, 마운트가 끝난 이 시점에 한 번 더 확인한다.
#
# 2. **베이스 이미지의 entrypoint 를 대신한다.** nvcr.io/nvidia/isaac-sim 의 기본
#    entrypoint 는 EULA 안내를 찍은 뒤 Isaac Sim 을 세그폴트로 떨어뜨린다 --
#    ACCEPT_EULA=Y 를 줘도 그렇다(2026-08-24 실측: 최소 예제조차 exit 139).
#    그 entrypoint 를 거치지 않으면 같은 이미지가 그대로 뜬다. EULA 동의는
#    .env 의 ACCEPT_EULA 로 참가자가 직접 표시한다.
set -e

if [ ! -L "${ISAACLAB_PATH}/_isaac_sim" ]; then
    ln -sf "${ISAACSIM_ROOT_PATH}" "${ISAACLAB_PATH}/_isaac_sim"
fi

if [ "${ACCEPT_EULA}" != "Y" ] && [ "${ACCEPT_EULA}" != "y" ]; then
    echo "NVIDIA Omniverse EULA 에 동의해야 Isaac Sim 이 실행됩니다." >&2
    echo "  https://docs.omniverse.nvidia.com/platform/latest/common/NVIDIA_Omniverse_License_Agreement.html" >&2
    echo "docker/.env 의 ACCEPT_EULA 를 Y 로 두고 docker compose up -d 를 다시 실행하세요." >&2
    exit 1
fi

exec "$@"
