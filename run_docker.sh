#!/usr/bin/env bash
# Run the ur5-hande-sim container with GUI (Gazebo + RViz) forwarded to your X
# display. Requires nvidia-container-toolkit + an NVIDIA GPU on the host for
# Gazebo Harmonic to render at usable speed.

set -e

IMAGE="${IMAGE:-ur5-hande-sim:latest}"

# Allow X11 from local containers (revoke after with `xhost -local:root`)
xhost +local:root >/dev/null

docker run --rm -it \
    --gpus all \
    --net=host \
    --env DISPLAY="${DISPLAY:-:0}" \
    --env QT_X11_NO_MITSHM=1 \
    --env XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" \
    --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
    --volume "${XAUTHORITY:-$HOME/.Xauthority}:/root/.Xauthority:rw" \
    --device /dev/dri:/dev/dri \
    "$IMAGE" "$@"
