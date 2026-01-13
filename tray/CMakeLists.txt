cmake_minimum_required(VERSION 3.10)
project(TrayApp)

set(CMAKE_CXX_STANDARD 17)

# 设置Unicode定义
add_definitions(-DUNICODE -D_UNICODE)

# 添加可执行文件（添加WIN32标志以隐藏控制台窗口，适用于最终发布版本）
add_executable(TrayApp WIN32 tray_app.cpp)

# 链接必要的Windows库
target_link_libraries(TrayApp 
    shlwapi
    user32
    gdi32
    shell32
    ole32
    oleaut32
    uuid
    comdlg32
    advapi32
    kernel32
    winspool
)