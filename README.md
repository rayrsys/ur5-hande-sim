# ur5-hande-sim

Drop-in bringup for a **Universal Robots UR5** with a **Robotiq Hand-E** gripper:
Gazebo Harmonic simulation, MoveIt 2 motion planning, ROS 2 Jazzy.

The same workspace drives the real lab arm — just clone the hardware driver and
flip `sim_gazebo` off.

## What's in here

| File / dir | Purpose |
|---|---|
| `urdf/ur5_hande.urdf.xacro` | Sim model — UR5 + Hand-E with built-in coupler, single `gz_ros2_control` plugin |
| `urdf/ur5_hande_real.urdf.xacro` | Real-hw model — same kinematics, uses `ur_robot_driver` + Modbus Hand-E plugins |
| `srdf/ur5_hande.srdf.xacro` | MoveIt SRDF — extends `ur_manipulator` group, adds `gripper` end-effector, disables collisions on adjacent Hand-E links |
| `config/ur5_hande_controllers.yaml` | Sim controllers: `joint_state_broadcaster` + `scaled_joint_trajectory_controller` + `hande_gripper_controller` |
| `config/ur5_hande_real_controllers.yaml` | Real-hw controllers: full UR stack (GPIO, speed scaling, F/T, TCP pose, force mode, freedrive, passthrough) + Hand-E |
| `config/kinematics.yaml` | TRAC-IK with `solve_type: Distance` — predictable IK, no random wrist flips |
| `launch/ur5_hande_gz.launch.py` | Spawns Gazebo, model, controllers, optionally MoveIt |
| `launch/ur5_hande_real.launch.py` | Real-hw bring-up: control_node, dashboard, urscript_interface, controller_stopper, tool_comm, spawners, optional MoveIt |
| `launch/ur5_hande_moveit.launch.py` | MoveIt 2 with our SRDF + kinematics override (used by both sim and real launches) |
| `patches/01-add-sim-gazebo-arg.patch` | Adds `sim_gazebo:=true` branch (`gz_ros2_control/GazeboSimSystem`) to the upstream Hand-E description |
| `setup.sh` | One-shot: apt deps + clone Hand-E repos + apply patches |
| `run_sim.sh` | Local launch wrapper — strips snap-leaked env vars (VS Code terminal etc.) so RViz/Gazebo don't crash on glibc mismatch |
| `Dockerfile` + `run_docker.sh` | Containerized full stack (sim only — driver isn't built in the image) |

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

## Real hardware (sim → real)

> ⚠ **Status: not yet validated on a physical robot.**
>
> What's been tested:
> - Sim path (Gazebo, MoveIt, gripper action) end-to-end ✅
> - The real-hw launch (`ur5_hande_real.launch.py`) has been **dry-run with
>   `use_mock_hardware:=true`** — all 14 controllers load, the controller_manager
>   stands up, the URDF parses, the gripper action server registers ✅
>
> What hasn't been tested:
> - Connecting to an actual UR controller over RTDE/URScript
> - The Hand-E Modbus path through the UR tool I/O + `socat`
> - Calibration extraction
> - Sending real motion commands to a physical arm
>
> If you're the first to plug this into hardware, expect to debug. Read the
> [first-run checklist](#first-run-checklist) below carefully. Open an issue (or
> PR) with whatever you hit.

The same workspace drives the physical lab arm. There's a dedicated launch:
`ur5_hande_real.launch.py`. It uses the same merged controllers (so anything
written against the sim — MoveIt plans, gripper actions, scripted trajectories —
runs unchanged) but swaps the hardware plugins:

| | Sim | Real |
|---|---|---|
| Arm | `gz_ros2_control/GazeboSimSystem` | `ur_robot_driver/URPositionHardwareInterface` (RTDE/URScript over TCP) |
| Gripper | `gz_ros2_control/GazeboSimSystem` | `robotiq_hande_driver/RobotiqHandeHardwareInterface` (Modbus RTU through UR tool I/O via `socat`) |
| Helpers | none | UR dashboard client, controller_stopper, urscript_interface, robot_state_helper, tool_communication |

### One-time prep on the robot

1. **Install `externalcontrol-x.x.x.urcap`** on the teach pendant.
   Download from
   [Universal_Robots_ROS2_Driver/ur_robot_driver/resources](https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver/tree/jazzy/ur_robot_driver/resources)
   onto a USB stick → on the pendant: *Setup Robot → URCaps → +* → install.
2. **Set up the External Control program** on the pendant: create a new program
   that consists of just the `External Control` URCap node. Set the host IP to
   the IP of the workstation running ROS. Save it.
3. **Set robot to Remote Control** mode (top-right menu on the pendant).
4. **Wire the Hand-E** through the UR tool I/O — 24V, GND, RS-485 A/B. With
   `use_tool_communication:=true` (the default), `ur_robot_driver` opens a TCP
   socket that `socat` pipes to `/tmp/ttyUR`, and `robotiq_hande_driver` Modbus-RTU's
   over that pseudo-tty. No external USB-RS485 dongle needed.

### Calibration (do this once per arm)

The default UR5 kinematics in `ur_description` are nominal — your TCP frame can
be off by ~mm. Pull the actual numbers from the controller:

```bash
ros2 launch ur_calibration calibration_correction.launch.py \
    robot_ip:=<UR-IP> \
    target_filename:="$HOME/ur5_calibration.yaml"
```

Pass the resulting YAML on every real launch (`kinematics_params_file:=...`).

### Network

ROS workstation and UR controller on the same subnet. Confirm:

```bash
ping <UR-IP>
nc -zv <UR-IP> 29999    # dashboard server
```

### Launch

```bash
source /opt/ros/jazzy/setup.bash
source ~/ur5_ws/install/setup.bash

ros2 launch ur5_hande_bringup ur5_hande_real.launch.py \
    robot_ip:=192.168.1.102 \
    kinematics_params_file:=$HOME/ur5_calibration.yaml \
    ur_type:=ur5
```

Then **on the teach pendant** press **Play** on the External Control program.
Once it's running, ROS controllers go active and you can plan in MoveIt RViz the
same way as in sim.

### Useful flags

```bash
launch_moveit:=false                    # skip MoveIt
launch_rviz:=false                      # no RViz (still spawns Gazebo's, on real-hw there is none)
use_mock_hardware:=true                 # dry-run the real-hw launch without an actual robot —
                                        #   verifies wiring, URDF, and controllers without needing the lab
use_tool_communication:=false           # Hand-E NOT wired through tool I/O (e.g. external RS-485 dongle —
                                        #   then also set tool_device_name:=/dev/ttyUSB0 or similar)
tool_voltage:=0                         # do not power the tool (default is 24V for Hand-E)
ur_type:=ur5e                           # e-Series instead of CB-series
```

### Verify everything is talking

In another terminal:

```bash
source /opt/ros/jazzy/setup.bash && source ~/ur5_ws/install/setup.bash

ros2 control list_controllers          # all 7+ controllers should be active or inactive
ros2 topic echo /joint_states          # arm joints + robotiq_hande_left_finger_joint
ros2 topic echo /ft_data               # 6-axis F/T from the wrist
ros2 topic echo /tcp_pose              # tool0 in base frame

# Open the Hand-E
ros2 action send_goal /hande_gripper_controller/gripper_cmd \
    control_msgs/action/ParallelGripperCommand \
    "{command: {name: ['robotiq_hande_left_finger_joint'], position: [0.025]}}"
```

### First-run checklist

Plug into the real arm in *this order*. If any step fails, fix it before moving on.

1. **Dry-run first, no hardware.** Confirm the launch is healthy on your
   workstation independent of the robot:
   ```bash
   ros2 launch ur5_hande_bringup ur5_hande_real.launch.py \
       robot_ip:=192.168.1.102 \
       use_mock_hardware:=true \
       launch_dashboard_client:=false \
       use_tool_communication:=false \
       launch_rviz:=false launch_moveit:=false
   ```
   Expected: 14 controllers loaded (7 active + 7 inactive), no plugin-load errors,
   `/hande_gripper_controller/gripper_cmd` action present. If this fails, the
   real run definitely won't work — fix the build / deps first.

2. **Network reachable.** `ping <UR-IP>` from the workstation. `nc -zv <UR-IP> 29999`
   should connect to the dashboard server. If those don't work, no ROS launch will.

3. **URCap installed and program ready.** On the teach pendant: *Setup Robot →
   URCaps* should list `External Control`. Open or create a program containing
   only the `External Control` URCap node, set the host IP to the workstation,
   save it, and **load** it. Don't press Play yet.

4. **Robot in Remote Control.** Top-right menu on the pendant → *Remote Control*.
   Without this, `ur_robot_driver` can't push URScript.

5. **Hand-E powered.** Tool flange connector wired to the gripper:
   - Pin 1 (24V) → gripper VDC
   - Pin 2 (0V) → gripper GND
   - Pin 4 (RS-485 A) → gripper RS-485+
   - Pin 6 (RS-485 B) → gripper RS-485−

   Verify with the pendant: *Installation → General → Tool I/O → set Tool Output
   to 24V*, the Hand-E LED should come on.

6. **Calibration extracted** (skip first time if you only want a no-load motion test):
   ```bash
   ros2 launch ur_calibration calibration_correction.launch.py \
       robot_ip:=<UR-IP> target_filename:=$HOME/ur5_calibration.yaml
   ```
   Without this, expect ~mm-level TCP offset.

7. **Launch.** With **only the arm** first (skip the gripper Modbus path on the
   very first try, ratchet up complexity gradually):
   ```bash
   ros2 launch ur5_hande_bringup ur5_hande_real.launch.py \
       robot_ip:=<UR-IP> \
       kinematics_params_file:=$HOME/ur5_calibration.yaml \
       use_tool_communication:=false \
       tool_voltage:=0
   ```
   Then **press Play** on the External Control program on the pendant.
   Expected: `External Control` URCap turns green, controller_manager logs
   "Successful 'activate' of hardware 'ur5'", `/joint_states` reports the actual
   arm pose.

8. **Test arm motion** with a tiny goal in RViz before adding the gripper —
   prove the URScript pipeline works.

9. **Add the gripper.** Re-launch with `use_tool_communication:=true tool_voltage:=24`
   (the defaults). The Hand-E driver will spin up `socat` against `/tmp/ttyUR`
   and do Modbus auto-init. Send an open command; if Modbus times out, check
   the slave ID (we use `9` per Hand-E factory default — change in `ur5_hande_real.urdf.xacro`
   if your gripper is set to a different ID).

### Known unknowns when going live

These are areas where the published config is "best-guess from documentation"
and may need tuning on your specific lab arm:

- **Modbus slave_id = 9** in `ur5_hande_real.urdf.xacro`. Hand-E factory default
  is 9; verify with Robotiq User Manual or by querying the gripper.
- **`tool_voltage = 24`** — default for Hand-E. **0** is safer for first plug-in
  (won't fry anything if wiring is wrong); only enable 24V after you've verified
  pinout.
- **`tool_baud_rate = 115200`** — Hand-E ships at this rate. Some lab grippers
  may have been reconfigured; you'd see Modbus framing errors.
- **`headless_mode = false`** — leave as-is unless you can't run the External
  Control URCap (e.g. no pendant available). Headless mode bypasses the URCap
  but loses some safety integration.
- **`safety_limits = true`** — leave on. Prevents the planner from generating
  motions outside the safety zone the pendant has configured.

### What's still UR-specific in the real-hw config

`io_and_status_controller`, `speed_scaling_state_broadcaster`,
`force_torque_sensor_broadcaster`, `tcp_pose_broadcaster`, `ur_configuration_controller`
are all real-UR-only state broadcasters. They're loaded but spawned automatically
by the real launch — they don't appear in the sim launch because Gazebo's
hardware plugin doesn't expose those interfaces.

`scaled_joint_trajectory_controller` works in both. On real hardware it honors
the speed-scaling slider on the pendant; in sim the `speed_scaling_interface_name`
is empty so it acts like a regular `JointTrajectoryController`.

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
