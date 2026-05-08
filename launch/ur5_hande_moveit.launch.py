"""MoveIt 2 launch for the combined UR5 + Robotiq Hand-E model.

Mirrors ur_moveit_config/launch/ur_moveit.launch.py but loads our extended SRDF
(ur5_hande.srdf.xacro) which adds the Hand-E end-effector group and disables
self-collisions between adjacent gripper links.
"""

import os
from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder


def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    abs_path = os.path.join(package_path, file_path)
    try:
        with open(abs_path) as f:
            return yaml.safe_load(f)
    except OSError:
        return None


def declare_arguments():
    return LaunchDescription(
        [
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            DeclareLaunchArgument(
                "ur_type",
                default_value="ur5",
                choices=["ur3", "ur5", "ur10", "ur3e", "ur5e", "ur10e", "ur16e", "ur20", "ur30"],
            ),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("publish_robot_description_semantic", default_value="true"),
        ]
    )


def generate_launch_description():
    launch_rviz = LaunchConfiguration("launch_rviz")
    ur_type = LaunchConfiguration("ur_type")
    use_sim_time = LaunchConfiguration("use_sim_time")
    publish_rds = LaunchConfiguration("publish_robot_description_semantic")

    bringup_share = Path(get_package_share_directory("ur5_hande_bringup"))
    srdf_path = bringup_share / "srdf" / "ur5_hande.srdf.xacro"
    kinematics_path = bringup_share / "config" / "kinematics.yaml"

    moveit_config = (
        MoveItConfigsBuilder(robot_name="ur", package_name="ur_moveit_config")
        .robot_description_semantic(srdf_path, {"name": ur_type})
        .robot_description_kinematics(kinematics_path)
        .to_moveit_configs()
    )

    ld = LaunchDescription()
    ld.add_entity(declare_arguments())

    wait_robot_description = Node(
        package="ur_robot_driver",
        executable="wait_for_robot_description",
        output="screen",
    )
    ld.add_action(wait_robot_description)

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {
                "use_sim_time": use_sim_time,
                "publish_robot_description_semantic": publish_rds,
            },
        ],
    )

    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare("ur_moveit_config"), "config", "moveit.rviz"]
    )
    rviz_node = Node(
        package="rviz2",
        condition=IfCondition(launch_rviz),
        executable="rviz2",
        name="rviz2_moveit",
        output="log",
        arguments=["-d", rviz_config_file],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
            {"use_sim_time": use_sim_time},
        ],
    )

    ld.add_action(
        RegisterEventHandler(
            OnProcessExit(
                target_action=wait_robot_description,
                on_exit=[move_group_node, rviz_node],
            )
        ),
    )

    return ld
