# UR5 + Robotiq Hand-E sim — ROS 2 Jazzy + Gazebo Harmonic + MoveIt 2.
#
# Build:  docker build -t ur5-hande-sim .
# Run:    ./run_docker.sh
#
# Needs nvidia-container-toolkit on the host for GPU rendering.

FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=all

RUN apt-get update && apt-get install -y --no-install-recommends \
      git \
      python3-colcon-common-extensions \
      python3-vcstool \
      ros-jazzy-ur \
      ros-jazzy-ur-simulation-gz \
      ros-jazzy-ur-moveit-config \
      ros-jazzy-moveit \
      ros-jazzy-moveit-py \
      ros-jazzy-ros-gz \
      ros-jazzy-gz-ros2-control \
      ros-jazzy-ros2-control \
      ros-jazzy-ros2-controllers \
      ros-jazzy-controller-manager \
      ros-jazzy-joint-state-broadcaster \
      ros-jazzy-joint-trajectory-controller \
      ros-jazzy-parallel-gripper-controller \
      ros-jazzy-gripper-controllers \
      ros-jazzy-trac-ik-kinematics-plugin \
      ros-jazzy-xacro \
      ros-jazzy-robot-state-publisher \
      ros-jazzy-rviz2 \
      libmodbus-dev \
      socat \
    && rm -rf /var/lib/apt/lists/*

# Workspace skeleton
RUN mkdir -p /ws/src
WORKDIR /ws/src

# Copy the bringup package (this repo)
COPY . /ws/src/ur5_hande_bringup/

# Pull upstream Hand-E deps and apply patches
RUN vcs import --skip-existing < /ws/src/ur5_hande_bringup/.repos && \
    cd /ws/src/robotiq_hande_description && \
    for p in /ws/src/ur5_hande_bringup/patches/*.patch; do \
      git apply "$p"; \
    done

# Build (skip the real-hw driver — Gazebo plugin handles sim)
WORKDIR /ws
RUN /bin/bash -c "source /opt/ros/jazzy/setup.bash && \
    colcon build --symlink-install \
      --packages-skip robotiq_hande_driver \
      --cmake-args -DCMAKE_BUILD_TYPE=Release"

COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/ws/src/ur5_hande_bringup/run_sim.sh"]
