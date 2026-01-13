#define UNICODE
#define _UNICODE

#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>  // 用于 SHGetFolderPath
#include <iostream>
#include <string>
#include <vector>
#include <locale>
#include <codecvt>
#include <fstream>
#include <sstream>
#include <algorithm>  // for std::min and std::max
#include <ctime>      // for logging timestamp

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "shell32.lib")

#define WM_TRAYICON (WM_USER + 1)
#define WM_LOOP_TIMER (WM_USER + 2)
#define ID_MENU_GRADE_CHANGED 1001
#define ID_MENU_GRADE_ALL 1002
#define ID_MENU_REFRESH_GRADE 1003
#define ID_MENU_SCHEDULE_TODAY 1004
#define ID_MENU_SCHEDULE_TOMORROW 1005
#define ID_MENU_SCHEDULE_FULL 1006
#define ID_MENU_REFRESH_SCHEDULE 1007
#define ID_MENU_EXIT 1008
#define ID_MENU_OPEN_CONFIG 1009
#define ID_MENU_EDIT_CONFIG 1010
#define TIMER_LOOP_CHECK 1001

NOTIFYICONDATAW nid;
HWND hwnd;

// 日志文件路径
std::string g_log_file_path;

// 循环检测配置结构体
struct LoopConfig {
    bool grade_enabled = false;
    int grade_interval = 3600;
    bool schedule_enabled = false;
    int schedule_interval = 3600;
};

LoopConfig g_loop_config;

// 日志函数
void LogMessage(const std::string& level, const std::string& message) {
    // 获取当前时间
    time_t now = time(nullptr);
    char timestamp[64];
    struct tm timeinfo;
    localtime_s(&timeinfo, &now);
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", &timeinfo);
    
    // 构建日志消息
    std::string log_line = std::string(timestamp) + " [" + level + "] " + message + "\n";
    
    // 输出到控制台（调试用）
    std::cout << log_line;
    
    // 写入日志文件
    if (!g_log_file_path.empty()) {
        std::ofstream log_file(g_log_file_path, std::ios::app);
        if (log_file.is_open()) {
            log_file << log_line;
            log_file.close();
        }
    }
}

#define LOG_INFO(msg) LogMessage("INFO", msg)
#define LOG_DEBUG(msg) LogMessage("DEBUG", msg)
#define LOG_ERROR(msg) LogMessage("ERROR", msg)
#define LOG_WARNING(msg) LogMessage("WARNING", msg)

// 函数前向声明
std::string GetExecutableDirectory();
void ExecutePythonCommand(const std::string& command_suffix);
void ExecuteConfigGui();
void EditConfigFile();
void InitializeLog();
void EnsureAppDataDirectory();
void ReadLoopConfig();
int GetMinLoopInterval();
void ExecuteLoopCheck();
bool CheckPythonEnvironment();
LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);

// 确保 AppData 目录存在
void EnsureAppDataDirectory() {
    char appdata_path[MAX_PATH];
    if (SHGetFolderPathA(NULL, CSIDL_LOCAL_APPDATA, NULL, 0, appdata_path) == S_OK) {
        std::string appdata_dir = std::string(appdata_path) + "\\GradeTracker";
        
        // 创建应用目录
        BOOL result = CreateDirectoryA(appdata_dir.c_str(), NULL);
        if (result || GetLastError() == ERROR_ALREADY_EXISTS) {
            LOG_INFO("AppData 目录已确保存在: " + appdata_dir);
        } else {
            LOG_WARNING("无法创建 AppData 目录: " + appdata_dir);
        }
    } else {
        LOG_WARNING("无法获取 AppData 目录路径");
    }
}

// 初始化日志系统
void InitializeLog() {
    // 优先使用用户 AppData\Local 目录（有写入权限）
    char appdata_path[MAX_PATH];
    if (SHGetFolderPathA(NULL, CSIDL_LOCAL_APPDATA, NULL, 0, appdata_path) == S_OK) {
        std::string log_dir = std::string(appdata_path) + "\\GradeTracker";
        
        // 创建应用目录
        CreateDirectoryA(log_dir.c_str(), NULL);
        
        g_log_file_path = log_dir + "\\tray_app.log";
        LOG_INFO("使用 AppData 目录: " + log_dir);
    } else {
        // 备选方案：使用程序所在目录
        std::string exe_dir = GetExecutableDirectory();
        g_log_file_path = exe_dir + "\\tray_app.log";
        LOG_WARNING("无法获取 AppData 目录，使用程序目录: " + exe_dir);
    }
    
    // 创建或清空日志文件（每次启动时）
    std::ofstream log_file(g_log_file_path, std::ios::trunc);
    if (log_file.is_open()) {
        log_file << "========== Tray App Started ==========\n";
        log_file.close();
        LOG_INFO("托盘应用程序启动");
        LOG_INFO("日志文件位置: " + g_log_file_path);
    } else {
        // 如果仍无法创建日志，尝试临时目录
        char temp_path[MAX_PATH];
        GetTempPathA(MAX_PATH, temp_path);
        g_log_file_path = std::string(temp_path) + "tray_app.log";
        
        std::ofstream fallback_log_file(g_log_file_path, std::ios::trunc);
        if (fallback_log_file.is_open()) {
            fallback_log_file << "========== Tray App Started (Temp) ==========\n";
            fallback_log_file.close();
            LOG_WARNING("日志文件位置(临时目录): " + g_log_file_path);
        } else {
            std::cout << "❌ 无法创建日志文件: " << g_log_file_path << std::endl;
        }
    }
}

// 读取配置文件
void ReadLoopConfig() {
    LOG_INFO("开始读取循环检测配置");
    
    // 优先从 AppData 目录读取配置文件
    char appdata_path[MAX_PATH];
    std::string config_path;
    
    if (SHGetFolderPathA(NULL, CSIDL_LOCAL_APPDATA, NULL, 0, appdata_path) == S_OK) {
        std::string appdata_config_dir = std::string(appdata_path) + "\\GradeTracker";
        config_path = appdata_config_dir + "\\config.ini";
        LOG_DEBUG("尝试从 AppData 目录读取配置: " + config_path);
        
        // 检查 AppData 目录中的配置文件是否存在
        std::ifstream appdata_config_file(config_path);
        if (!appdata_config_file.is_open()) {
            LOG_WARNING("AppData 目录中未找到配置文件，回退到程序目录");
            // 回退到程序目录
            std::string exe_dir = GetExecutableDirectory();
            config_path = exe_dir + "\\config.ini";
        } else {
            appdata_config_file.close();
        }
    } else {
        // 如果无法获取 AppData 目录，使用程序目录
        std::string exe_dir = GetExecutableDirectory();
        config_path = exe_dir + "\\config.ini";
        LOG_WARNING("无法获取 AppData 目录，使用程序目录: " + exe_dir);
    }
    
    LOG_DEBUG("配置文件路径: " + config_path);
    
    std::ifstream config_file(config_path);
    if (!config_file.is_open()) {
        LOG_WARNING("无法打开配置文件: " + config_path);
        return;
    }
    
    std::string line;
    std::string current_section;
    
    while (std::getline(config_file, line)) {
        // 移除行首尾空格
        line.erase(0, line.find_first_not_of(" \t\r\n"));
        line.erase(line.find_last_not_of(" \t\r\n") + 1);
        
        if (line.empty() || line[0] == ';' || line[0] == '#') {
            continue;
        }
        
        // 检测章节
        if (line[0] == '[' && line[line.length() - 1] == ']') {
            current_section = line.substr(1, line.length() - 2);
            continue;
        }
        
        // 解析键值对
        size_t pos = line.find('=');
        if (pos != std::string::npos) {
            std::string key = line.substr(0, pos);
            std::string value = line.substr(pos + 1);
            
            // 移除键值周围的空格
            key.erase(0, key.find_first_not_of(" \t"));
            key.erase(key.find_last_not_of(" \t") + 1);
            value.erase(0, value.find_first_not_of(" \t"));
            value.erase(value.find_last_not_of(" \t") + 1);
            
            if (current_section == "loop_getCourseGrades") {
                if (key == "enabled") {
                    g_loop_config.grade_enabled = (value == "True" || value == "true" || value == "1");
                    LOG_DEBUG("成绩循环检测开关: " + std::string(g_loop_config.grade_enabled ? "true" : "false"));
                } else if (key == "time") {
                    g_loop_config.grade_interval = std::stoi(value);
                    LOG_DEBUG("成绩循环检测间隔: " + std::to_string(g_loop_config.grade_interval) + "秒");
                }
            } else if (current_section == "loop_getCourseSchedule") {
                if (key == "enabled") {
                    g_loop_config.schedule_enabled = (value == "True" || value == "true" || value == "1");
                    LOG_DEBUG("课表循环检测开关: " + std::string(g_loop_config.schedule_enabled ? "true" : "false"));
                } else if (key == "time") {
                    g_loop_config.schedule_interval = std::stoi(value);
                    LOG_DEBUG("课表循环检测间隔: " + std::to_string(g_loop_config.schedule_interval) + "秒");
                }
            }
        }
    }
    
    config_file.close();
    LOG_INFO("循环检测配置读取完成");
}

// 计算最小循环间隔（毫秒）
int GetMinLoopInterval() {
    LOG_DEBUG("计算最小循环间隔");
    int min_interval = INT_MAX;
    
    if (g_loop_config.grade_enabled && g_loop_config.grade_interval > 0) {
        if (g_loop_config.grade_interval < min_interval) {
            min_interval = g_loop_config.grade_interval;
        }
    }
    
    if (g_loop_config.schedule_enabled && g_loop_config.schedule_interval > 0) {
        if (g_loop_config.schedule_interval < min_interval) {
            min_interval = g_loop_config.schedule_interval;
        }
    }
    
    // 如果没有启用任何循环检测，返回0
    if (min_interval == INT_MAX) {
        LOG_INFO("未启用循环检测");
        return 0;
    }
    
    // 转换为毫秒，但至少检查一次（60秒），最备3600秒
    if (min_interval < 60) {
        min_interval = 60;
    }
    if (min_interval > 3600) {
        min_interval = 3600;
    }
    
    LOG_INFO("循环检测间隔设置为: " + std::to_string(min_interval) + "秒");
    return min_interval * 1000;
}

// 执行循环检测
void ExecuteLoopCheck() {
    LOG_INFO("开始执行循环检测");
    
    if (g_loop_config.grade_enabled) {
        LOG_DEBUG("执行成绩检测");
        ExecutePythonCommand("--fetch-grade");
    }
    
    if (g_loop_config.schedule_enabled) {
        LOG_DEBUG("执行课表检测");
        ExecutePythonCommand("--fetch-schedule");
    }
    
    LOG_INFO("循环检测完成");
}

// 获取可执行文件所在目录
std::string GetExecutableDirectory() {
    wchar_t exe_path[MAX_PATH];
    GetModuleFileNameW(NULL, exe_path, MAX_PATH);
    std::wstring wstr_exe_path(exe_path);
    size_t pos = wstr_exe_path.find_last_of(L"\\/");
    if (pos != std::string::npos) {
        wstr_exe_path = wstr_exe_path.substr(0, pos);
    }
    // 转换为UTF-8
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, &wstr_exe_path[0], (int)wstr_exe_path.size(), NULL, 0, NULL, NULL);
    std::string str_path(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, &wstr_exe_path[0], (int)wstr_exe_path.size(), &str_path[0], size_needed, NULL, NULL);
    return str_path;
}

// 检查Python脚本是否存在
bool CheckPythonEnvironment() {
    LOG_DEBUG("检查 Python 环境");
    std::string exe_dir = GetExecutableDirectory();
    std::string pythonw_path = exe_dir + "\\.venv\\Scripts\\pythonw.exe";
    std::string script_path = exe_dir + "\\core\\go.py";
    
    LOG_DEBUG("Python 路径: " + pythonw_path);
    LOG_DEBUG("脚本路径: " + script_path);
    
    // 检查Python解释器和脚本是否存在
    DWORD pythonw_attr = GetFileAttributesA(pythonw_path.c_str());
    DWORD script_attr = GetFileAttributesA(script_path.c_str());
    
    bool result = (pythonw_attr != INVALID_FILE_ATTRIBUTES) && (script_attr != INVALID_FILE_ATTRIBUTES);
    LOG_DEBUG("Python 环境检查结果: " + std::string(result ? "成功" : "失败"));
    return result;
}

// 执行Python脚本（无窗口模式）
void ExecutePythonCommand(const std::string& command_suffix) {
    LOG_INFO("执行 Python 命令: " + command_suffix);
    
    if (!CheckPythonEnvironment()) {
        LOG_ERROR("Python 环境未正确安装");
        MessageBoxA(NULL, "Python环境未正确安装！\n请重新运行安装程序。", "错误", MB_OK | MB_ICONERROR);
        return;
    }
    
    std::string exe_dir = GetExecutableDirectory();
    std::string pythonw_path = exe_dir + "\\.venv\\Scripts\\pythonw.exe";
    std::string script_path = exe_dir + "\\core\\go.py";
    std::string full_command = "\"" + pythonw_path + "\" \"" + script_path + "\" " + command_suffix;
    
    LOG_DEBUG("完整命令: " + full_command);
    
    // 使用CreateProcess以无窗口方式执行
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;  // 隐藏窗口
    ZeroMemory(&pi, sizeof(pi));
    
    // 创建进程
    if (CreateProcessA(NULL, (LPSTR)full_command.c_str(), NULL, NULL, FALSE, 
                       CREATE_NO_WINDOW, NULL, exe_dir.c_str(), &si, &pi)) {
        LOG_INFO("Python 进程启动成功");
        // 不等待进程结束，立即关闭句柄
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    } else {
        DWORD error = GetLastError();
        LOG_ERROR("Python 进程启动失败，错误代码: " + std::to_string(error));
    }
}

// 打开配置界面
void ExecuteConfigGui() {
    LOG_INFO("打开配置界面");
    std::string exe_dir = GetExecutableDirectory();
    std::string pythonw_path = exe_dir + "\\.venv\\Scripts\\pythonw.exe";
    std::string gui_path = exe_dir + "\\gui\\gui.py";

    DWORD pythonw_attr = GetFileAttributesA(pythonw_path.c_str());
    DWORD gui_attr = GetFileAttributesA(gui_path.c_str());

    if (pythonw_attr == INVALID_FILE_ATTRIBUTES || gui_attr == INVALID_FILE_ATTRIBUTES) {
        LOG_ERROR("配置界面文件不存在");
        MessageBoxA(NULL, "配置界面所需的 Python 环境未正确安装！\n请重新运行安装程序。", "错误", MB_OK | MB_ICONERROR);
        return;
    }

    // 构建命令行
    std::string full_command = "\"" + pythonw_path + "\" \"" + gui_path + "\"";

    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_SHOW;  // 显示窗口（GUI程序需要可见）
    ZeroMemory(&pi, sizeof(pi));

    // 启动GUI程序（虚拟环境已包含所有依赖）
    if (CreateProcessA(NULL, (LPSTR)full_command.c_str(), NULL, NULL, FALSE,
                       0, NULL, exe_dir.c_str(), &si, &pi)) {
        LOG_INFO("配置界面启动成功");
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    } else {
        DWORD error = GetLastError();
        LOG_ERROR("配置界面启动失败，错误代码: " + std::to_string(error));
        char error_msg[256];
        sprintf_s(error_msg, "无法启动配置工具！\n错误代码：%lu\n请检查Python环境是否正确安装。", error);
        MessageBoxA(NULL, error_msg, "错误", MB_OK | MB_ICONERROR);
    }
}

// 用记事本打开配置文件
void EditConfigFile() {
    LOG_INFO("打开配置文件编辑器");
    std::string exe_dir = GetExecutableDirectory();
    std::string config_path = exe_dir + "\\config.ini";

    DWORD config_attr = GetFileAttributesA(config_path.c_str());
    if (config_attr == INVALID_FILE_ATTRIBUTES) {
        LOG_ERROR("配置文件不存在");
        MessageBoxA(NULL, "配置文件不存在！\n请先使用配置工具创建配置。", "错误", MB_OK | MB_ICONERROR);
        return;
    }

    LOG_DEBUG("使用记事本打开: " + config_path);
    // 使用 ShellExecuteA 打开记事本
    ShellExecuteA(NULL, "open", "notepad.exe", config_path.c_str(), NULL, SW_SHOW);
}

// 将std::string转换为std::wstring
std::wstring s2ws(const std::string& str) {
    int size_needed = MultiByteToWideChar(CP_UTF8, 0, &str[0], (int)str.size(), NULL, 0);
    std::wstring wstrTo(size_needed, 0);
    MultiByteToWideChar(CP_UTF8, 0, &str[0], (int)str.size(), &wstrTo[0], size_needed);
    return wstrTo;
}

LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_CREATE:
        {
            LOG_INFO("初始化托盘图标");
            // 初始化托盘图标
            ZeroMemory(&nid, sizeof(NOTIFYICONDATAW));
            nid.cbSize = sizeof(NOTIFYICONDATAW);
            nid.hWnd = hwnd;
            nid.uID = 1;
            nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
            nid.uCallbackMessage = WM_TRAYICON;
            wcscpy_s(nid.szTip, L"学业助手");
            
            // 加载图标（如果没有图标文件，使用系统默认）
            HICON hIcon = LoadIcon(NULL, IDI_APPLICATION);
            nid.hIcon = hIcon;
            
            Shell_NotifyIcon(NIM_ADD, &nid);
            LOG_INFO("托盘图标添加成功");
            
            // 读取循环检测配置
            ReadLoopConfig();
            
            // 如果启用了循环检测，设置定时器
            int interval = GetMinLoopInterval();
            if (interval > 0) {
                LOG_INFO("设置循环检测定时器，间隔: " + std::to_string(interval) + "ms");
                SetTimer(hwnd, TIMER_LOOP_CHECK, interval, NULL);
            }
            break;
        }
        
        case WM_TIMER:
        {
            if (wParam == TIMER_LOOP_CHECK) {
                LOG_DEBUG("定时器触发，执行循环检测");
                ExecuteLoopCheck();
            }
            break;
        }
            
        case WM_TRAYICON:
        {
            if (LOWORD(lParam) == WM_RBUTTONDOWN) {
                LOG_DEBUG("托盘图标右键菜单打开");
                POINT pt;
                GetCursorPos(&pt);
                SetForegroundWindow(hwnd);
                
                HMENU hMenu = CreatePopupMenu();
                AppendMenuW(hMenu, MF_STRING, ID_MENU_GRADE_CHANGED, L"推送变化的成绩");
                AppendMenuW(hMenu, MF_STRING, ID_MENU_GRADE_ALL, L"推送全部成绩");
                AppendMenuW(hMenu, MF_STRING, ID_MENU_REFRESH_GRADE, L"刷新成绩");
                AppendMenuW(hMenu, MF_SEPARATOR, 0, NULL);
                AppendMenuW(hMenu, MF_STRING, ID_MENU_SCHEDULE_TODAY, L"推送今天课表");
                AppendMenuW(hMenu, MF_STRING, ID_MENU_SCHEDULE_TOMORROW, L"推送明天课表");
                AppendMenuW(hMenu, MF_STRING, ID_MENU_SCHEDULE_FULL, L"推送本学期全部课表");
                AppendMenuW(hMenu, MF_STRING, ID_MENU_REFRESH_SCHEDULE, L"刷新课表");
                AppendMenuW(hMenu, MF_SEPARATOR, 0, NULL);
                AppendMenuW(hMenu, MF_STRING, ID_MENU_OPEN_CONFIG, L"打开配置工具");
                AppendMenuW(hMenu, MF_STRING, ID_MENU_EDIT_CONFIG, L"更改配置文件");
                AppendMenuW(hMenu, MF_SEPARATOR, 0, NULL);
                AppendMenuW(hMenu, MF_STRING, ID_MENU_EXIT, L"退出");
                
                TrackPopupMenu(hMenu, TPM_RIGHTBUTTON, pt.x, pt.y, 0, hwnd, NULL);
                DestroyMenu(hMenu);
            }
            break;
        }
            
        case WM_COMMAND:
        {
            int menu_id = LOWORD(wParam);
            LOG_INFO("菜单选项被点击， ID: " + std::to_string(menu_id));
            
            switch (menu_id) {
                case ID_MENU_GRADE_CHANGED:
                    ExecutePythonCommand("--push-grade --force");
                    break;
                case ID_MENU_GRADE_ALL:
                    ExecutePythonCommand("--fetch-grade --force");
                    break;
                case ID_MENU_REFRESH_GRADE:
                    ExecutePythonCommand("--fetch-grade --force");
                    break;
                case ID_MENU_SCHEDULE_TODAY:
                    ExecutePythonCommand("--fetch-schedule --force");
                    break;
                case ID_MENU_SCHEDULE_TOMORROW:
                    ExecutePythonCommand("--push-schedule --force");
                    break;
                case ID_MENU_SCHEDULE_FULL:
                    ExecutePythonCommand("--fetch-schedule --force");
                    break;
                case ID_MENU_REFRESH_SCHEDULE:
                    ExecutePythonCommand("--fetch-schedule --force");
                    break;
                case ID_MENU_OPEN_CONFIG:
                    ExecuteConfigGui();
                    break;
                case ID_MENU_EDIT_CONFIG:
                    EditConfigFile();
                    break;
                case ID_MENU_EXIT:
                    LOG_INFO("用户选择退出");
                    KillTimer(hwnd, TIMER_LOOP_CHECK);
                    Shell_NotifyIcon(NIM_DELETE, &nid);
                    PostQuitMessage(0);
                    break;
            }
            break;
        }
            
        case WM_DESTROY:
        {
            LOG_INFO("窗口销毁，清理资源");
            KillTimer(hwnd, TIMER_LOOP_CHECK);
            Shell_NotifyIcon(NIM_DELETE, &nid);
            PostQuitMessage(0);
            break;
        }
            
        default:
            return DefWindowProc(hwnd, msg, wParam, lParam);
    }
    return 0;
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    // 初始化日志系统
    InitializeLog();
    
    // 确保 AppData 目录存在
    EnsureAppDataDirectory();
    
    LOG_INFO("========== 应用程序开始启动 ==========");
    
    // 创建互斥量防止多次启动
    HANDLE hMutex = CreateMutexW(NULL, TRUE, L"GradeTrackerTrayAppMutex");
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        LOG_WARNING("程序已经在运行中");
        // 程序已经在运行
        MessageBoxW(NULL, 
                    L"学业助手托盘程序已经在运行中！\n如果看不到托盘图标，请检查任务管理器。",
                    L"提示",
                    MB_OK | MB_ICONINFORMATION);
        if (hMutex) {
            CloseHandle(hMutex);
        }
        return 0;
    }
    
    const wchar_t CLASS_NAME[] = L"TrayAppClass";
    
    LOG_INFO("注册窗口类");
    WNDCLASSW wc = {};
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = CLASS_NAME;
    
    RegisterClassW(&wc);
    
    LOG_INFO("创建主窗口");
    hwnd = CreateWindowExW(
        0,
        CLASS_NAME,
        L"学业助手托盘程序",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT,
        NULL,
        NULL,
        hInstance,
        NULL
    );
    
    LOG_INFO("进入消息循环");
    MSG msg = {};
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    
    LOG_INFO("应用程序退出，释放互斥量");
    // 释放互斥量
    if (hMutex) {
        ReleaseMutex(hMutex);
        CloseHandle(hMutex);
    }
    
    return 0;
}