# ur5-hande-sim

Drop-in bringup for a **Universal Robots UR5** with a **Robotiq Hand-E** gripper:
Gazebo Harmonic simulation, MoveIt 2 motion planning, ROS 2 Jazzy.

The same workspace drives the real lab arm — just clone the hardware driver and
flip `sim_gazebo` off.

## What's in here

| File / dir | Purpose |
|---|---|
| `urdf/ur5_hande.urdf.xacro` | Top-level model — UR5 + Hand-E (with built-in coupler), single `gz_ros2_control` plugin |
| `srdf/ur5_hande.srdf.xacro` | MoveIt SRDF — extends `ur_manipulator` group, adds `gripper` end-effector group, disables collisions on adjacent Hand-E links |
| `config/ur5_hande_controllers.yaml` | `joint_state_broadcaster` + `scaled_joint_trajectory_controller` (arm) + `hande_gripper_controller` (Hand-E) |
| `config/kinematics.yaml` | TRAC-IK with `solve_type: Distance` — predictable IK, no random wrist flips |
| `launch/ur5_hande_gz.launch.py` | Spawns Gazebo, model, controllers, optionally MoveIt |
| `launch/ur5_hande_moveit.launch.py` | MoveIt 2 with our SRDF + kinematics override |
| `patches/01-add-sim-gazebo-arg.patch` | Adds `sim_gazebo:=true` branch (`gz_ros2_control/GazeboSimSystem`) to the upstream Hand-E description |
| `setup.sh` | One-shot: apt deps + clone Hand-E repos + apply patches |
| `run_sim.sh` | Local launch wrapper — strips snap-leaked env vars (VS Code terminal etc.) so RViz/Gazebo don't crash on glibc mismatch |
| `Dockerfile` + `run_docker.sh` | Containerized full stack |

## Requirements

- **Ubuntu 24.04** with **ROS 2 Jazzy** installed (`sudo apt install ros-jazzy-ros-base` and `source /opt/ros/jazzy/setup.bash`).
- **NVIDIA GPU** strongly recommended for Gazebo Harmonic. CPU rendering works but is slow.
- For the Docker path: `docker` + `nvidia-container-toolkit`.

## Quick start (native install)

```bash
# 1. Create a colcon workspace and clone this repo into it
mkdir -p ~/ur5_ws/src && cd ~/ur5_ws/src
git clone https://github.com/<YOUR_GITHUB_USERNAME>/ur5-hande-sim.git ur5_hande_bringup

# 2. Pull deps + apply patches + apt install (will sudo for apt)
./ur5_hande_bringup/setup.sh

# 3. Build (skips the real-hw driver; not needed for sim)
cd ~/ur5_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-skip robotiq_hande_driver
source install/setup.bash

# 4. Run
~/ur5_ws/src/ur5_hande_bringup/run_sim.sh
```

You should get Gazebo Harmonic + RViz with MoveIt's MotionPlanning panel.
Wait for `You can start planning now!` in the launch log.

### Useful launch flags

```bash
./run_sim.sh launch_moveit:=false           # skip MoveIt — Gazebo + controllers only
./run_sim.sh launch_rviz:=false             # no RViz
./run_sim.sh gazebo_gui:=false              # gz server only (headless)
./run_sim.sh ur_type:=ur5e                  # use the e-Series kinematics
./run_sim.sh arm_controller:=joint_trajectory_controller   # plain JTC instead of UR-scaled
```

## Quick start (Docker)

```bash
# Build the image (~2 GB, ~5 min first time)
docker build -t ur5-hande-sim ~/ur5_ws/src/ur5_hande_bringup

# Launch the full sim with GUI + GPU
~/ur5_ws/src/ur5_hande_bringup/run_docker.sh

# Or override the entrypoint to drop into a shell
~/ur5_ws/src/ur5_hande_bringup/run_docker.sh bash
```

`run_docker.sh` handles X11 forwarding (`/tmp/.X11-unix` + `XAUTHORITY`) and GPU
passthrough (`--gpus all`). On first launch it'll grant the container access via
`xhost +local:root`; revoke after with `xhost -local:root` if you care.

## Controlling the gripper

Open another terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ur5_ws/install/setup.bash

# OPEN (50 mm gap)
ros2 action send_goal /hande_gripper_controller/gripper_cmd \
  control_msgs/action/ParallelGripperCommand \
  "{command: {name: ['robotiq_hande_left_finger_joint'], position: [0.025]}}"

# CLOSE (fingers touch)
ros2 action send_goal /hande_gripper_controller/gripper_cmd \
  control_msgs/action/ParallelGripperCommand \
  "{command: {name: ['robotiq_hande_left_finger_joint'], position: [0.0]}}"
```

Position is in **meters**, range `[0.0, 0.025]` per finger (50 mm total stroke).

## Driving the arm

- **From RViz** (easiest): MotionPlanning panel → Planning tab → drag the orange marker → **Plan** → **Execute**. For motion that looks like a teach-pendant move, change **Planning Pipeline** from `ompl` to `pilz_industrial_motion_planner` and pick **PTP**.
- **From the CLI**: send a `FollowJointTrajectory` goal to `/scaled_joint_trajectory_controller/follow_joint_trajectory`.
- **From code**: use `moveit_py` or `moveit_ros_planning_interface`.

## Real Hand-E hardware

The driver isn't built by default. When you're ready:

```bash
sudo apt install -y libmodbus-dev socat ros-jazzy-gripper-controllers
cd ~/ur5_ws
colcon build --symlink-install --packages-select robotiq_hande_driver
```

Then in `urdf/ur5_hande.urdf.xacro` flip `sim_gazebo:=false` (and adjust the `tty_port` / `socat_*` params to match your tool I/O), and launch without Gazebo.

## Known limitations

- **dartsim doesn't support `mimic` joints.** Gazebo Harmonic's default physics ignores the mimic that ties the right finger to the left, so visually only the left finger moves. The action server still reports correct state and your controller still works. Switch the gz physics engine to `bullet-featherstone` if you need both fingers symmetric.
- **VS Code's snap terminal leaks `GTK_PATH` / `LOCPATH` / `XDG_DATA_DIRS` / `GIO_MODULE_DIR`** pointing into `/snap/code/...`, which causes RViz to load an old `libpthread` from `/snap/core20/` and crash with `__libc_pthread_init`. The `run_sim.sh` wrapper strips those vars. If you launch via `ros2 launch` directly from a snap-confined terminal, expect a crash.
- **First launch after an `apt upgrade`** can hit a fastcdr ABI mismatch (Gazebo crashes with `undefined symbol: _ZN8eprosima7fastcdr3Cdr9serializeEj`). Fix with another full `sudo apt upgrade -y`.

## Credit

Built on top of:
- [`UniversalRobots/Universal_Robots_ROS2_Driver`](https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver) — UR description, controllers, MoveIt config (BSD-3-Clause)
- [`UniversalRobots/Universal_Robots_ROS2_GZ_Simulation`](https://github.com/UniversalRobots/Universal_Robots_ROS2_GZ_Simulation) — UR Gazebo bringup (BSD-3-Clause)
- [`macmacal/robotiq_hande_description`](https://github.com/macmacal/robotiq_hande_description) — Hand-E URDF + meshes (Apache-2.0)
- [`AGH-CEAI/robotiq_hande_driver`](https://github.com/AGH-CEAI/robotiq_hande_driver) — Hand-E hardware driver (Apache-2.0)
- [`ros-controls/ros2_control`](https://github.com/ros-controls/ros2_control), [`gz_ros2_control`](https://github.com/ros-controls/gz_ros2_control), [`moveit2`](https://github.com/moveit/moveit2)

## License

Apache-2.0. See `LICENSE`.
# ur5-hande-sim
