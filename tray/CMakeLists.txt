cmake_minimum_required(VERSION 3.10)
project(Capture_Push_tray)

set(CMAKE_CXX_STANDARD 17)

# 读取 VERSION 文件并设置为变量
file(READ "../VERSION" VERSION_CONTENT)
string(STRIP "${VERSION_CONTENT}" APP_VERSION)
message(STATUS "Detected app version: ${APP_VERSION}")

# 设置Unicode定义
add_definitions(-DUNICODE -D_UNICODE)

# 定义版本宏供 C++ 代码使用
add_definitions(-DAPP_VERSION="\${APP_VERSION}")

# 强制 MSVC 使用 UTF-8 编码处理源文件和字符串
if(MSVC)
    add_compile_options(/utf-8)
endif()

# 添加可执行文件（添加WIN32标志以隐藏控制台窗口，适用于最终发布版本）
add_executable(Capture_Push_tray WIN32 tray_app.cpp resources.rc)

# 链接必要的Windows库
target_link_libraries(Capture_Push_tray 
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