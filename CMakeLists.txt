cmake_minimum_required(VERSION 3.16)
project(ur5_hande_bringup)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf config launch srdf
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
