cmake_minimum_required(VERSION 3.10)
project(TrayApp)

set(CMAKE_CXX_STANDARD 17)

# 设置Unicode定义
add_definitions(-DUNICODE -D_UNICODE)

# 添加可执行文件（WIN32表示这是Windows GUI应用，使用WinMain入口）
add_executable(TrayApp WIN32 tray_app.cpp)

# 链接必要的Windows库
target_link_libraries(TrayApp shlwapi)