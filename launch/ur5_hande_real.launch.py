"""Real-hardware launch for UR5 + Robotiq Hand-E.

Self-contained — no IncludeLaunchDescription of ur_control.launch.py — because
upstream's RSP launch only passes robot_ip + ur_type and doesn't let us swap the
description xacro for ours. Mirrors the structure of ur_robot_driver/launch/
ur_control.launch.py (control_node, dashboard_client, urscript_interface,
controller_stopper, robot_state_helper, tool_communication, RSP, controller
spawners, RViz) and adds the Hand-E gripper controller to the spawn list.

Required args:
  robot_ip:=<UR-IP>          IP of the UR controller
  kinematics_params_file:=<absolute-path>   YAML produced by ur_calibration

Optional:
  ur_type:=ur5               (default ur5; pick ur5e for e-Series)
  use_mock_hardware:=true    (dry-run without an actual robot)
  launch_moveit:=true        (default true)
  launch_rviz:=true
"""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import (
    AnyLaunchDescriptionSource,
    PythonLaunchDescriptionSource,
)
from launch.substitutions import (
    AndSubstitution,
    Command,
    FindExecutable,
    LaunchConfiguration,
    NotSubstitution,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile, ParameterValue
from launch_ros.substitutions import FindPackageShare


def launch_setup(context):
    ur_type = LaunchConfiguration("ur_type")
    robot_ip = LaunchConfiguration("robot_ip")
    safety_limits = LaunchConfiguration("safety_limits")
    safety_pos_margin = LaunchConfiguration("safety_pos_margin")
    safety_k_position = LaunchConfiguration("safety_k_position")

    description_file = LaunchConfiguration("description_file")
    controllers_file = LaunchConfiguration("controllers_file")
    update_rate_config_file = LaunchConfiguration("update_rate_config_file")

    tf_prefix = LaunchConfiguration("tf_prefix")
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    mock_sensor_commands = LaunchConfiguration("mock_sensor_commands")
    headless_mode = LaunchConfiguration("headless_mode")

    initial_joint_controller = LaunchConfiguration("initial_joint_controller")
    activate_joint_controller = LaunchConfiguration("activate_joint_controller")
    controller_spawner_timeout = LaunchConfiguration("controller_spawner_timeout")

    launch_dashboard_client = LaunchConfiguration("launch_dashboard_client")
    launch_rviz = LaunchConfiguration("launch_rviz")
    launch_moveit = LaunchConfiguration("launch_moveit")

    # Tool I/O — Hand-E hangs off the UR tool serial. Default ON.
    use_tool_communication = LaunchConfiguration("use_tool_communication")
    tool_parity = LaunchConfiguration("tool_parity")
    tool_baud_rate = LaunchConfiguration("tool_baud_rate")
    tool_stop_bits = LaunchConfiguration("tool_stop_bits")
    tool_rx_idle_chars = LaunchConfiguration("tool_rx_idle_chars")
    tool_tx_idle_chars = LaunchConfiguration("tool_tx_idle_chars")
    tool_device_name = LaunchConfiguration("tool_device_name")
    tool_tcp_port = LaunchConfiguration("tool_tcp_port")
    tool_voltage = LaunchConfiguration("tool_voltage")

    reverse_ip = LaunchConfiguration("reverse_ip")
    script_command_port = LaunchConfiguration("script_command_port")
    reverse_port = LaunchConfiguration("reverse_port")
    script_sender_port = LaunchConfiguration("script_sender_port")
    trajectory_port = LaunchConfiguration("trajectory_port")

    kinematics_params_file = LaunchConfiguration("kinematics_params_file")

    script_filename = PathJoinSubstitution(
        [FindPackageShare("ur_client_library"), "resources", "external_control.urscript"]
    )
    input_recipe_filename = PathJoinSubstitution(
        [FindPackageShare("ur_robot_driver"), "resources", "rtde_input_recipe.txt"]
    )
    output_recipe_filename = PathJoinSubstitution(
        [FindPackageShare("ur_robot_driver"), "resources", "rtde_output_recipe.txt"]
    )

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ", description_file,
            " ", "name:=", ur_type,
            " ", "ur_type:=", ur_type,
            " ", "tf_prefix:=", tf_prefix,
            " ", "robot_ip:=", robot_ip,
            " ", "kinematics_params:=", kinematics_params_file,
            " ", "safety_limits:=", safety_limits,
            " ", "safety_pos_margin:=", safety_pos_margin,
            " ", "safety_k_position:=", safety_k_position,
            " ", "use_mock_hardware:=", use_mock_hardware,
            " ", "mock_sensor_commands:=", mock_sensor_commands,
            " ", "headless_mode:=", headless_mode,
            " ", "script_filename:=", script_filename,
            " ", "input_recipe_filename:=", input_recipe_filename,
            " ", "output_recipe_filename:=", output_recipe_filename,
            " ", "use_tool_communication:=", use_tool_communication,
            " ", "tool_parity:=", tool_parity,
            " ", "tool_baud_rate:=", tool_baud_rate,
            " ", "tool_stop_bits:=", tool_stop_bits,
            " ", "tool_rx_idle_chars:=", tool_rx_idle_chars,
            " ", "tool_tx_idle_chars:=", tool_tx_idle_chars,
            " ", "tool_device_name:=", tool_device_name,
            " ", "tool_tcp_port:=", tool_tcp_port,
            " ", "tool_voltage:=", tool_voltage,
            " ", "reverse_ip:=", reverse_ip,
            " ", "script_command_port:=", script_command_port,
            " ", "reverse_port:=", reverse_port,
            " ", "script_sender_port:=", script_sender_port,
            " ", "trajectory_port:=", trajectory_port,
        ]
    )
    robot_description = {
        "robot_description": ParameterValue(robot_description_content, value_type=str),
    }

    # ros2_control: hosts both UR + Hand-E hardware components in one controller_manager
    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            update_rate_config_file,
            ParameterFile(controllers_file, allow_substs=True),
        ],
        output="screen",
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description],
    )

    dashboard_client_node = IncludeLaunchDescription(
        condition=IfCondition(
            AndSubstitution(launch_dashboard_client, NotSubstitution(use_mock_hardware))
        ),
        launch_description_source=AnyLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ur_robot_driver"), "launch", "ur_dashboard_client.launch.py"]
            )
        ),
        launch_arguments={"robot_ip": robot_ip}.items(),
    )

    robot_state_helper_node = Node(
        package="ur_robot_driver",
        executable="robot_state_helper",
        name="ur_robot_state_helper",
        output="screen",
        condition=UnlessCondition(use_mock_hardware),
        parameters=[
            {"headless_mode": headless_mode},
            {"robot_ip": robot_ip},
        ],
    )

    tool_communication_node = Node(
        package="ur_robot_driver",
        condition=IfCondition(use_tool_communication),
        executable="tool_communication.py",
        name="ur_tool_comm",
        output="screen",
        parameters=[
            {
                "robot_ip": robot_ip,
                "tcp_port": tool_tcp_port,
                "device_name": tool_device_name,
            }
        ],
    )

    urscript_interface = Node(
        package="ur_robot_driver",
        executable="urscript_interface",
        parameters=[{"robot_ip": robot_ip}],
        output="screen",
        condition=UnlessCondition(use_mock_hardware),
    )

    controller_stopper_node = Node(
        package="ur_robot_driver",
        executable="controller_stopper_node",
        name="controller_stopper",
        output="screen",
        emulate_tty=True,
        condition=UnlessCondition(use_mock_hardware),
        parameters=[
            {"headless_mode": headless_mode},
            {"joint_controller_active": activate_joint_controller},
            {
                # Controllers in this list are kept active even when the arm
                # disconnects. The gripper is independent of the UR comms layer
                # (it talks Modbus over the tool I/O) so we keep it consistent.
                "consistent_controllers": [
                    "io_and_status_controller",
                    "force_torque_sensor_broadcaster",
                    "joint_state_broadcaster",
                    "speed_scaling_state_broadcaster",
                    "tcp_pose_broadcaster",
                    "ur_configuration_controller",
                    "hande_gripper_controller",
                ]
            },
        ],
    )

    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare("ur_description"), "rviz", "view_robot.rviz"]
    )
    rviz_node = Node(
        package="rviz2",
        condition=IfCondition(launch_rviz),
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
    )

    def controller_spawner(controllers, active=True):
        return Node(
            package="controller_manager",
            executable="spawner",
            arguments=[
                "--controller-manager", "/controller_manager",
                "--controller-manager-timeout", controller_spawner_timeout,
            ]
            + (["--inactive"] if not active else [])
            + controllers,
        )

    controllers_active = [
        "joint_state_broadcaster",
        "io_and_status_controller",
        "speed_scaling_state_broadcaster",
        "force_torque_sensor_broadcaster",
        "tcp_pose_broadcaster",
        "ur_configuration_controller",
        "hande_gripper_controller",
    ]
    controllers_inactive = [
        "scaled_joint_trajectory_controller",
        "joint_trajectory_controller",
        "forward_velocity_controller",
        "forward_position_controller",
        "forward_effort_controller",
        "force_mode_controller",
        "passthrough_trajectory_controller",
        "freedrive_mode_controller",
        "tool_contact_controller",
    ]
    if activate_joint_controller.perform(context) == "true":
        chosen = initial_joint_controller.perform(context)
        controllers_active.append(chosen)
        if chosen in controllers_inactive:
            controllers_inactive.remove(chosen)
    if use_mock_hardware.perform(context) == "true":
        # tcp_pose_broadcaster requires the real UR; mock hardware doesn't expose it.
        if "tcp_pose_broadcaster" in controllers_active:
            controllers_active.remove("tcp_pose_broadcaster")

    moveit_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ur5_hande_bringup"), "launch", "ur5_hande_moveit.launch.py"]
            )
        ),
        launch_arguments={
            "ur_type": ur_type,
            "use_sim_time": "false",
            "launch_rviz": launch_rviz,
        }.items(),
        condition=IfCondition(launch_moveit),
    )

    return [
        control_node,
        robot_state_publisher_node,
        dashboard_client_node,
        robot_state_helper_node,
        tool_communication_node,
        urscript_interface,
        controller_stopper_node,
        rviz_node,
        moveit_launch,
        controller_spawner(controllers_active),
        controller_spawner(controllers_inactive, active=False),
    ]


def generate_launch_description():
    decl = [
        DeclareLaunchArgument(
            "ur_type",
            default_value="ur5",
            choices=["ur3", "ur5", "ur10", "ur3e", "ur5e", "ur10e", "ur16e", "ur20", "ur30"],
            description="Type/series of UR robot.",
        ),
        DeclareLaunchArgument(
            "robot_ip",
            description="IP address by which the UR controller can be reached.",
        ),
        DeclareLaunchArgument(
            "kinematics_params_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("ur_description"), "config",
                 LaunchConfiguration("ur_type"), "default_kinematics.yaml"]
            ),
            description="ABSOLUTE path to the calibration YAML for THIS robot. "
                        "Generate via `ros2 launch ur_calibration calibration_correction.launch.py "
                        "robot_ip:=... target_filename:=...`. Default is the generic UR5 kinematics — "
                        "your TCP will not be accurate without your own calibration.",
        ),
        DeclareLaunchArgument(
            "description_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("ur5_hande_bringup"), "urdf", "ur5_hande_real.urdf.xacro"]
            ),
        ),
        DeclareLaunchArgument(
            "controllers_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("ur5_hande_bringup"), "config",
                 "ur5_hande_real_controllers.yaml"]
            ),
        ),
        DeclareLaunchArgument(
            "update_rate_config_file",
            default_value=[
                PathJoinSubstitution([FindPackageShare("ur_robot_driver"), "config"]),
                "/", LaunchConfiguration("ur_type"), "_update_rate.yaml",
            ],
        ),
        DeclareLaunchArgument("safety_limits", default_value="true"),
        DeclareLaunchArgument("safety_pos_margin", default_value="0.15"),
        DeclareLaunchArgument("safety_k_position", default_value="20"),
        DeclareLaunchArgument("tf_prefix", default_value=""),
        DeclareLaunchArgument(
            "use_mock_hardware",
            default_value="false",
            description="Dry-run: bring everything up against UR's mock hw plugin (no real robot).",
        ),
        DeclareLaunchArgument("mock_sensor_commands", default_value="false"),
        DeclareLaunchArgument("headless_mode", default_value="false"),
        DeclareLaunchArgument(
            "initial_joint_controller",
            default_value="scaled_joint_trajectory_controller",
            choices=[
                "scaled_joint_trajectory_controller",
                "joint_trajectory_controller",
                "forward_velocity_controller",
                "forward_position_controller",
                "freedrive_mode_controller",
                "passthrough_trajectory_controller",
            ],
        ),
        DeclareLaunchArgument("activate_joint_controller", default_value="true"),
        DeclareLaunchArgument("controller_spawner_timeout", default_value="10"),
        DeclareLaunchArgument("launch_dashboard_client", default_value="true"),
        DeclareLaunchArgument("launch_rviz", default_value="true"),
        DeclareLaunchArgument(
            "launch_moveit",
            default_value="true",
            description="Also start MoveIt 2 with our SRDF + TRAC-IK kinematics.",
        ),

        # tool I/O — defaults are tuned for Robotiq Hand-E over the UR tool serial port
        DeclareLaunchArgument("use_tool_communication", default_value="true"),
        DeclareLaunchArgument("tool_parity", default_value="0"),
        DeclareLaunchArgument("tool_baud_rate", default_value="115200"),
        DeclareLaunchArgument("tool_stop_bits", default_value="1"),
        DeclareLaunchArgument("tool_rx_idle_chars", default_value="1.5"),
        DeclareLaunchArgument("tool_tx_idle_chars", default_value="3.5"),
        DeclareLaunchArgument("tool_device_name", default_value="/tmp/ttyUR"),
        DeclareLaunchArgument("tool_tcp_port", default_value="54321"),
        DeclareLaunchArgument(
            "tool_voltage",
            default_value="24",
            description="24V powers the Hand-E from the UR tool flange. 0 = off.",
        ),

        DeclareLaunchArgument("reverse_ip", default_value="0.0.0.0"),
        DeclareLaunchArgument("script_command_port", default_value="50004"),
        DeclareLaunchArgument("reverse_port", default_value="50001"),
        DeclareLaunchArgument("script_sender_port", default_value="50002"),
        DeclareLaunchArgument("trajectory_port", default_value="50003"),
    ]
    return LaunchDescription(decl + [OpaqueFunction(function=launch_setup)])
