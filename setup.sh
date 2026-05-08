#!/usr/bin/env bash
# Pulls the upstream Robotiq Hand-E description + driver into ../ (sibling of
# this package), applies the gz_ros2_control patch to the description, and
# installs the apt deps. Run this once after cloning the repo.
#
# Layout produced (relative to your colcon workspace):
#   ws/src/ur5_hande_bringup/        ← this repo
#   ws/src/robotiq_hande_description/  ← upstream + patches
#   ws/src/robotiq_hande_driver/       ← upstream (only needed for real hw)
#
# Then in ws/:  source /opt/ros/jazzy/setup.bash && colcon build --symlink-install \
#                  --packages-skip robotiq_hande_driver

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(dirname "$HERE")"   # parent of this package = ws/src

echo "==> apt deps (sim + real-hw)"
sudo apt update
sudo apt install -y \
  ros-jazzy-ur ros-jazzy-ur-simulation-gz ros-jazzy-ur-moveit-config \
  ros-jazzy-moveit ros-jazzy-moveit-py \
  ros-jazzy-ros-gz ros-jazzy-gz-ros2-control \
  ros-jazzy-ros2-control ros-jazzy-ros2-controllers \
  ros-jazzy-controller-manager \
  ros-jazzy-joint-state-broadcaster ros-jazzy-joint-trajectory-controller \
  ros-jazzy-parallel-gripper-controller ros-jazzy-gripper-controllers \
  ros-jazzy-trac-ik-kinematics-plugin \
  ros-jazzy-xacro ros-jazzy-robot-state-publisher ros-jazzy-rviz2 \
  ros-jazzy-pose-broadcaster ros-jazzy-force-torque-sensor-broadcaster \
  libmodbus-dev socat \
  python3-colcon-common-extensions python3-vcstool

echo
echo "==> cloning Hand-E deps into $SRC_DIR"
cd "$SRC_DIR"
vcs import --skip-existing < "$HERE/.repos"

echo
echo "==> applying patches to robotiq_hande_description"
DESC_DIR="$SRC_DIR/robotiq_hande_description"
cd "$DESC_DIR"
for p in "$HERE"/patches/*.patch; do
  if git apply --check "$p" 2>/dev/null; then
    echo "  applying $(basename "$p")"
    git apply "$p"
  elif git apply --reverse --check "$p" 2>/dev/null; then
    echo "  $(basename "$p") already applied — skipping"
  else
    echo "  WARN: $(basename "$p") does not apply cleanly. Inspect manually."
    exit 1
  fi
done

echo
echo "Done. Build the workspace with:"
echo "  cd $(dirname "$SRC_DIR")"
echo "  source /opt/ros/jazzy/setup.bash"
echo "  colcon build --symlink-install        # builds everything including the real-hw driver"
echo "  source install/setup.bash"
echo
echo "Then run:"
echo "  $HERE/run_sim.sh                      # Gazebo + MoveIt simulation"
echo "  ros2 launch ur5_hande_bringup ur5_hande_real.launch.py \\"
echo "      robot_ip:=<your-UR-IP> \\"
echo "      kinematics_params_file:=<your-calibration.yaml>      # real hardware"
echo
echo "Skip the real-hw driver to build faster (sim-only) with:"
echo "  colcon build --symlink-install --packages-skip robotiq_hande_driver"
