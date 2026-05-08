#!/usr/bin/env bash
# Launches the UR5 + Hand-E sim with a snap-clean environment.
# Needed because VS Code's snap (or other snap-confined terminal) leaks
# GTK_PATH / LOCPATH / XDG_DATA_DIRS / GIO_MODULE_DIR pointing into
# /snap/code/.../usr, which causes rviz2 (Qt) to dlopen GTK plugins that
# transitively load /snap/core20/.../libpthread.so.0 — incompatible with
# the system glibc, so rviz2 crashes with:
#   "symbol lookup error: __libc_pthread_init, version GLIBC_PRIVATE"
#
# Usage:
#   ./run_sim.sh                        # full GUI + MoveIt + RViz
#   ./run_sim.sh launch_moveit:=false   # skip MoveIt
#   ./run_sim.sh gazebo_gui:=false launch_rviz:=false launch_moveit:=false  # headless

set -e
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

exec env -u GTK_PATH \
        -u GTK_IM_MODULE_FILE \
        -u GTK_EXE_PREFIX \
        -u GIO_MODULE_DIR \
        -u GIO_LAUNCHED_DESKTOP_FILE \
        -u LOCPATH \
        -u GSETTINGS_SCHEMA_DIR \
        -u XDG_DATA_HOME \
        -u XDG_DATA_DIRS \
        bash -c "
            source /opt/ros/jazzy/setup.bash
            source '$WS/install/setup.bash'
            ros2 launch ur5_hande_bringup ur5_hande_gz.launch.py $*
        "
