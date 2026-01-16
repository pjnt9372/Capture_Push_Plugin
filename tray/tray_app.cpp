#define NOMINMAX  // 修复：防止 Windows 头文件定义 min/max 宏干扰 std::min/max

#include <windows.h>
#include <shellapi.h>
#include <iostream>
#include <string>
#include <vector>
#include <locale>
#include <codecvt>
#include <fstream>
#include <sstream>
#include <algorithm>  // for std::min and std::max
#include <chrono>     // for time logging
#include <mutex>      // for thread-safe logging
#include <iomanip>    // for std::put_time
#include <Shlobj.h>   // for SHGetKnownFolderPath
#include <tlhelp32.h> // for process enumeration

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "ole32.lib")  // for CoTaskMemFree
#pragma comment(lib, "advapi32.lib")  // for registry functions

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

// 循环检测配置结构体
struct LoopConfig {
    bool grade_enabled = false;
    int grade_interval = 3600;
    bool schedule_enabled = false;
    int schedule_interval = 3600;
    bool push_today_8am = false;
    bool push_tomorrow_9pm = false;
    bool push_next_week_sunday = false;
};

LoopConfig g_loop_config;

// 全局日志流和互斥锁
std::ofstream g_log_file;
std::mutex g_log_mutex;

// 函数前向声明
std::string GetInstallPathFromRegistry();
std::string GetExecutableDirectory();
void ExecutePythonCommand(const std::string& command_suffix);
void ExecuteConfigGui();
void EditConfigFile();
void InitLogging();
void CloseLogging();
void LogMessage(const std::string& message);

// 检查是否已有同名进程在运行
bool IsProcessRunning(const wchar_t* processName) {
    bool exists = false;
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnapshot != INVALID_HANDLE_VALUE) {
        PROCESSENTRY32W pe;
        pe.dwSize = sizeof(PROCESSENTRY32W);
        if (Process32FirstW(hSnapshot, &pe)) {
            DWORD currentPid = GetCurrentProcessId();
            do {
                if (_wcsicmp(pe.szExeFile, processName) == 0 && pe.th32ProcessID != currentPid) {
                    exists = true;
                    break;
                }
            } while (Process32NextW(hSnapshot, &pe));
        }
        CloseHandle(hSnapshot);
    }
    return exists;
}

// 获取 %LOCALAPPDATA%\Capture_Push 路径并创建目录
std::string GetLogDirectory() {
    PWSTR localAppDataPath = nullptr;
    if (SUCCEEDED(SHGetKnownFolderPath(FOLDERID_LocalAppData, 0, NULL, &localAppDataPath))) {
        std::wstring logDirW(localAppDataPath);
        logDirW += L"\\Capture_Push";
        CreateDirectoryW(logDirW.c_str(), NULL); // 自动忽略已存在错误

        int size_needed = WideCharToMultiByte(CP_UTF8, 0, logDirW.c_str(), -1, NULL, 0, NULL, NULL);
        std::string logDirA(size_needed - 1, 0);
        WideCharToMultiByte(CP_UTF8, 0, logDirW.c_str(), -1, &logDirA[0], size_needed, NULL, NULL);

        CoTaskMemFree(localAppDataPath);
        return logDirA;
    }
    CoTaskMemFree(localAppDataPath);
    return "";
}

// 从注册表读取安装路径
std::string GetInstallPathFromRegistry() {
    HKEY hKey;
    // 尝试从 HKLM 读取
    LONG result = RegOpenKeyExA(HKEY_LOCAL_MACHINE, 
                                 "SOFTWARE\\Capture_Push", 
                                 0, KEY_READ, &hKey);
    
    if (result != ERROR_SUCCESS) {
        return "";
    }
    
    // 获取值的大小
    DWORD type, size = 0;
    result = RegQueryValueExA(hKey, "InstallPath", NULL, &type, NULL, &size);
    
    if (result != ERROR_SUCCESS) {
        RegCloseKey(hKey);
        return "";
    }
    
    // 读取值
    std::vector<char> buffer(size);
    result = RegQueryValueExA(hKey, "InstallPath", NULL, &type, 
                              reinterpret_cast<LPBYTE>(&buffer[0]), &size);
    
    RegCloseKey(hKey);
    
    if (result != ERROR_SUCCESS) {
        return "";
    }
    
    return std::string(buffer.data());
}

// 初始化日志系统
void InitLogging() {
    std::string logDir = GetLogDirectory();
    if (logDir.empty()) return;
    std::string logPath = logDir + "\\tray_app.log";  // 修复：使用正确的日志文件名
    g_log_file.open(logPath, std::ios::out | std::ios::app);
    if (g_log_file.is_open()) {
        g_log_file << "\n--- Log session started at " 
                   << std::string(__DATE__) << " " << std::string(__TIME__) << " ---\n";
        g_log_file.flush();
    }
}

// 关闭日志
void CloseLogging() {
    if (g_log_file.is_open()) {
        g_log_file << "--- Log session ended ---\n";
        g_log_file.close();
    }
}

// 安全日志写入（带时间戳，仅写入文件，可选择启用控制台输出）
void LogMessage(const std::string& message) {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()) % 1000;

    std::tm tm{};
#ifdef _MSC_VER
    localtime_s(&tm, &time_t);
#else
    tm = *std::localtime(&time_t);
#endif

    // 构建日志消息
    std::ostringstream log_stream;
    log_stream << std::put_time(&tm, "%Y-%m-%d %H:%M:%S")
               << '.' << std::setfill('0') << std::setw(3) << ms.count()
               << " | " << message;
    std::string log_line = log_stream.str();

    // 【调试选项】如需启用控制台输出，取消下面一行的注释
    // std::cout << log_line << std::endl;

    // 写入日志文件
    if (g_log_file.is_open()) {
        std::lock_guard<std::mutex> lock(g_log_mutex);
        g_log_file << log_line << '\n';
        g_log_file.flush();
    }
}

// 读取配置文件（从 AppData 目录）
void ReadLoopConfig() {
    LogMessage("Reading config.ini from AppData...");
    
    // 修复：从 AppData 目录读取配置文件
    std::string logDir = GetLogDirectory();
    if (logDir.empty()) {
        LogMessage("Failed to get AppData directory.");
        return;
    }
    std::string config_path = logDir + "\\config.ini";
    
    std::ifstream config_file(config_path);
    if (!config_file.is_open()) {
        LogMessage("config.ini not found in AppData: " + config_path);
        return;
    }
    
    std::string line;
    std::string current_section;
    
    while (std::getline(config_file, line)) {
        line.erase(0, line.find_first_not_of(" \t\r\n"));
        line.erase(line.find_last_not_of(" \t\r\n") + 1);
        
        if (line.empty() || line[0] == ';' || line[0] == '#') continue;
        
        if (line[0] == '[' && line.back() == ']') {
            current_section = line.substr(1, line.size() - 2);
            continue;
        }
        
        size_t pos = line.find('=');
        if (pos != std::string::npos) {
            std::string key = line.substr(0, pos);
            std::string value = line.substr(pos + 1);
            key.erase(0, key.find_first_not_of(" \t"));
            key.erase(key.find_last_not_of(" \t") + 1);
            value.erase(0, value.find_first_not_of(" \t"));
            value.erase(value.find_last_not_of(" \t") + 1);
            
            if (current_section == "loop_getCourseGrades") {
                if (key == "enabled") {
                    g_loop_config.grade_enabled = (value == "True" || value == "true" || value == "1");
                } else if (key == "time") {
                    g_loop_config.grade_interval = std::stoi(value);
                }
            } else if (current_section == "loop_getCourseSchedule") {
                if (key == "enabled") {
                    g_loop_config.schedule_enabled = (value == "True" || value == "true" || value == "1");
                } else if (key == "time") {
                    g_loop_config.schedule_interval = std::stoi(value);
                }
            } else if (current_section == "schedule_push") {
                if (key == "today_8am") {
                    g_loop_config.push_today_8am = (value == "True" || value == "true" || value == "1");
                } else if (key == "tomorrow_9pm") {
                    g_loop_config.push_tomorrow_9pm = (value == "True" || value == "true" || value == "1");
                } else if (key == "next_week_sunday") {
                    g_loop_config.push_next_week_sunday = (value == "True" || value == "true" || value == "1");
                }
            }
        }
    }
    config_file.close();
    LogMessage("Config loaded from AppData: grade_enabled=" + std::to_string(g_loop_config.grade_enabled) +
               ", schedule_enabled=" + std::to_string(g_loop_config.schedule_enabled));
}

// 计算最小循环间隔（毫秒）
int GetMinLoopInterval() {
    // 固定为 60 秒检查一次，因为我们要处理定时推送
    return 60 * 1000;
}

// 定时推送检查
void ExecuteScheduledPushCheck() {
    auto now = std::chrono::system_clock::now();
    std::time_t now_c = std::chrono::system_clock::to_time_t(now);
    std::tm now_tm;
#ifdef _MSC_VER
    localtime_s(&now_tm, &now_c);
#else
    now_tm = *std::localtime(&now_c);
#endif

    static int last_push_today_date = -1;    // YYYYMMDD
    static int last_push_tomorrow_date = -1; // YYYYMMDD
    static int last_push_next_week_date = -1; // YYYYMMDD

    int current_date = (now_tm.tm_year + 1900) * 10000 + (now_tm.tm_mon + 1) * 100 + now_tm.tm_mday;

    // 当天 8 点推送 (如果错过时间，只要在当天 8 点后且未推送过，就补发)
    if (g_loop_config.push_today_8am && now_tm.tm_hour >= 8 && last_push_today_date != current_date) {
        LogMessage("Scheduled task: Today's schedule push (Triggered/Catch-up)");
        ExecutePythonCommand("--push-today");
        last_push_today_date = current_date;
    }

    // 前一天 21 点推送明天课表 (如果错过时间，在 21 点后至午夜前补发)
    if (g_loop_config.push_tomorrow_9pm && now_tm.tm_hour >= 21 && last_push_tomorrow_date != current_date) {
        LogMessage("Scheduled task: Tomorrow's schedule push (Triggered/Catch-up)");
        ExecutePythonCommand("--push-tomorrow");
        last_push_tomorrow_date = current_date;
    }

    // 周日 20 点推送下周全部课表 (如果周日 20 点后错过，则在周日内补发)
    if (g_loop_config.push_next_week_sunday && now_tm.tm_wday == 0 && now_tm.tm_hour >= 20 && last_push_next_week_date != current_date) {
        LogMessage("Scheduled task: Next week schedule push (Triggered/Catch-up)");
        ExecutePythonCommand("--push-next-week");
        last_push_next_week_date = current_date;
    }
}

// 执行循环检测
void ExecuteLoopCheck() {
    LogMessage("Timer triggered: performing checks.");
    
    // 每次触发都重新读取配置，确保能及时响应 GUI 的修改
    ReadLoopConfig();
    
    // 1. 检查定时推送
    ExecuteScheduledPushCheck();

    // 2. 检查循环刷新
    static time_t last_grade_check = 0;
    static time_t last_schedule_check = 0;
    time_t now = time(NULL);

    if (g_loop_config.grade_enabled && (now - last_grade_check >= g_loop_config.grade_interval)) {
        LogMessage("Grade loop: fetching grades.");
        ExecutePythonCommand("--fetch-grade");
        last_grade_check = now;
    }
    
    if (g_loop_config.schedule_enabled && (now - last_schedule_check >= g_loop_config.schedule_interval)) {
        LogMessage("Schedule loop: fetching schedule.");
        ExecutePythonCommand("--fetch-schedule");
        last_schedule_check = now;
    }
}

// 获取可执行文件所在目录（优先从注册表读取）
std::string GetExecutableDirectory() {
    // 优先尝试从注册表读取安装路径
    std::string registry_path = GetInstallPathFromRegistry();
    if (!registry_path.empty()) {
        LogMessage("从注册表获取到安装路径: " + registry_path);
        return registry_path;
    }
    
    // 如果注册表读取失败，回退到原来的方法
    LogMessage("注册表读取失败，使用可执行文件目录");
    wchar_t exe_path[MAX_PATH];
    GetModuleFileNameW(NULL, exe_path, MAX_PATH);
    std::wstring wstr_exe_path(exe_path);
    size_t pos = wstr_exe_path.find_last_of(L"\\/");
    if (pos != std::string::npos) {
        wstr_exe_path = wstr_exe_path.substr(0, pos);
    }
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, &wstr_exe_path[0], (int)wstr_exe_path.size(), NULL, 0, NULL, NULL);
    std::string str_path(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, &wstr_exe_path[0], (int)wstr_exe_path.size(), &str_path[0], size_needed, NULL, NULL);
    return str_path;
}

// 检查Python脚本是否存在
bool CheckPythonEnvironment() {
    std::string exe_dir = GetExecutableDirectory();
    std::string pythonw_path = exe_dir + "\\.venv\\Scripts\\pythonw.exe";
    std::string script_path = exe_dir + "\\core\\go.py";
    DWORD pythonw_attr = GetFileAttributesA(pythonw_path.c_str());
    DWORD script_attr = GetFileAttributesA(script_path.c_str());
    return (pythonw_attr != INVALID_FILE_ATTRIBUTES) && (script_attr != INVALID_FILE_ATTRIBUTES);
}

// 执行Python脚本（无窗口模式）
void ExecutePythonCommand(const std::string& command_suffix) {
    LogMessage("Executing Python command: " + command_suffix);
    if (!CheckPythonEnvironment()) {
        LogMessage("Python environment check failed!");
        MessageBoxA(NULL, "Python环境未正确安装！\n请重新运行安装程序。", "错误", MB_OK | MB_ICONERROR);
        return;
    }
    
    std::string exe_dir = GetExecutableDirectory();
    std::string pythonw_path = exe_dir + "\\.venv\\Scripts\\pythonw.exe";
    std::string script_path = exe_dir + "\\core\\go.py";
    std::string full_command = "\"" + pythonw_path + "\" \"" + script_path + "\" " + command_suffix;
    
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    ZeroMemory(&pi, sizeof(pi));
    
    if (CreateProcessA(NULL, (LPSTR)full_command.c_str(), NULL, NULL, FALSE, 
                       CREATE_NO_WINDOW, NULL, exe_dir.c_str(), &si, &pi)) {
        LogMessage("Python process started successfully.");
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    } else {
        DWORD err = GetLastError();
        LogMessage("Failed to start Python process. Error: " + std::to_string(err));
    }
}

// 打开配置界面
void ExecuteConfigGui() {
    LogMessage("Launching config GUI...");
    std::string exe_dir = GetExecutableDirectory();
    std::string pythonw_path = exe_dir + "\\.venv\\Scripts\\pythonw.exe";
    std::string gui_path = exe_dir + "\\gui\\gui.py";

    if (GetFileAttributesA(pythonw_path.c_str()) == INVALID_FILE_ATTRIBUTES ||
        GetFileAttributesA(gui_path.c_str()) == INVALID_FILE_ATTRIBUTES) {
        LogMessage("Config GUI files missing.");
        MessageBoxA(NULL, "配置界面所需的 Python 环境未正确安装！\n请重新运行安装程序。", "错误", MB_OK | MB_ICONERROR);
        return;
    }

    std::string full_command = "\"" + pythonw_path + "\" \"" + gui_path + "\"";
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_SHOW;
    ZeroMemory(&pi, sizeof(pi));

    if (CreateProcessA(NULL, (LPSTR)full_command.c_str(), NULL, NULL, FALSE,
                       0, NULL, exe_dir.c_str(), &si, &pi)) {
        LogMessage("Config GUI launched.");
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    } else {
        DWORD error = GetLastError();
        LogMessage("Failed to launch config GUI. Error: " + std::to_string(error));
        char error_msg[256];
        sprintf_s(error_msg, "无法启动配置工具！\n错误代码：%lu\n请检查Python环境是否正确安装。", error);
        MessageBoxA(NULL, error_msg, "错误", MB_OK | MB_ICONERROR);
    }
}

// 用记事本打开配置文件（从 AppData 目录）
void EditConfigFile() {
    LogMessage("Opening config.ini in Notepad from AppData...");
    
    // 修复：从 AppData 目录读取配置文件
    std::string logDir = GetLogDirectory();
    if (logDir.empty()) {
        LogMessage("Failed to get AppData directory.");
        MessageBoxA(NULL, "无法获取 AppData 目录！", "错误", MB_OK | MB_ICONERROR);
        return;
    }
    std::string config_path = logDir + "\\config.ini";

    if (GetFileAttributesA(config_path.c_str()) == INVALID_FILE_ATTRIBUTES) {
        LogMessage("config.ini not found in AppData when trying to edit: " + config_path);
        MessageBoxA(NULL, "配置文件不存在！\n请先使用配置工具创建配置。", "错误", MB_OK | MB_ICONERROR);
        return;
    }

    LogMessage("Opening config file: " + config_path);
    ShellExecuteA(NULL, "open", "notepad.exe", config_path.c_str(), NULL, SW_SHOW);
}

// 将std::string转换为std::wstring（未使用，保留兼容性）
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
            ZeroMemory(&nid, sizeof(NOTIFYICONDATAW));
            nid.cbSize = sizeof(NOTIFYICONDATAW);
            nid.hWnd = hwnd;
            nid.uID = 1;
            nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
            nid.uCallbackMessage = WM_TRAYICON;
            wcscpy_s(nid.szTip, L"Capture_Push");
            nid.hIcon = LoadIcon(NULL, IDI_APPLICATION);
            Shell_NotifyIcon(NIM_ADD, &nid);
            
            ReadLoopConfig();
            int interval = GetMinLoopInterval();
            if (interval > 0) {
                SetTimer(hwnd, TIMER_LOOP_CHECK, interval, NULL);
                LogMessage("Loop timer set to " + std::to_string(interval / 1000) + " seconds.");
            }
            break;
        }
        
        case WM_TIMER:
        {
            if (wParam == TIMER_LOOP_CHECK) {
                ExecuteLoopCheck();
            }
            break;
        }
            
        case WM_TRAYICON:
        {
            if (LOWORD(lParam) == WM_RBUTTONDOWN) {
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
            switch (LOWORD(wParam)) {
                case ID_MENU_GRADE_CHANGED:
                    LogMessage("User selected: Push changed grades");
                    ExecutePythonCommand("--push-grade --force");
                    break;
                case ID_MENU_GRADE_ALL:
                    LogMessage("User selected: Push all grades");
                    ExecutePythonCommand("--push-all-grades --force");
                    break;
                case ID_MENU_REFRESH_GRADE:
                    LogMessage("User selected: Refresh grades");
                    ExecutePythonCommand("--fetch-grade --force");
                    break;
                case ID_MENU_SCHEDULE_TODAY:
                    LogMessage("User selected: Fetch today's schedule");
                    ExecutePythonCommand("--fetch-schedule --force");
                    break;
                case ID_MENU_SCHEDULE_TOMORROW:
                    LogMessage("User selected: Push tomorrow's schedule");
                    ExecutePythonCommand("--push-schedule --force");
                    break;
                case ID_MENU_SCHEDULE_FULL:
                    LogMessage("User selected: Fetch full schedule");
                    ExecutePythonCommand("--fetch-schedule --force");
                    break;
                case ID_MENU_REFRESH_SCHEDULE:
                    LogMessage("User selected: Refresh schedule");
                    ExecutePythonCommand("--fetch-schedule --force");
                    break;
                case ID_MENU_OPEN_CONFIG:
                    ExecuteConfigGui();
                    break;
                case ID_MENU_EDIT_CONFIG:
                    EditConfigFile();
                    break;
                case ID_MENU_EXIT:
                    LogMessage("User selected 'Exit'. Shutting down.");
                    KillTimer(hwnd, TIMER_LOOP_CHECK);
                    Shell_NotifyIcon(NIM_DELETE, &nid);
                    PostQuitMessage(0);
                    break;
            }
            break;
        }
            
        case WM_DESTROY:
        {
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
    // 【调试选项】如需启用控制台输出，取消下面几行的注释
    /*
    SetConsoleOutputCP(CP_UTF8);
    std::cout << "=== Capture_Push Tray App (Debug Mode) ===" << std::endl;
    std::cout << "Console logging enabled for debugging." << std::endl;
    */
    
    InitLogging();
    LogMessage("Application starting...");

    // 双重检查：互斥锁 + 进程列表检查
    HANDLE hMutex = CreateMutexW(NULL, TRUE, L"Capture_PushTrayAppMutex");
    bool alreadyRunning = (GetLastError() == ERROR_ALREADY_EXISTS);
    
    // 如果互斥锁显示已存在，或者检测到同名进程（排除自身）
    if (alreadyRunning || IsProcessRunning(L"Capture_Push_tray.exe")) {
        LogMessage("Another instance is already running. Exiting.");
        MessageBoxW(NULL, 
                    L"Capture_Push 托盘程序已经在运行中！\n如果看不到托盘图标，请检查任务管理器。",
                    L"提示",
                    MB_OK | MB_ICONINFORMATION);
        if (hMutex) CloseHandle(hMutex);
        CloseLogging();
        return 0;
    }
    
    const wchar_t CLASS_NAME[] = L"TrayAppClass";
    WNDCLASSW wc = {};
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = CLASS_NAME;
    RegisterClassW(&wc);
    
    hwnd = CreateWindowExW(0, CLASS_NAME, L"Capture_Push 托盘程序",
                           0, 0, 0, 0, 0, NULL, NULL, hInstance, NULL);
    
    MSG msg = {};
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    
    if (hMutex) {
        ReleaseMutex(hMutex);
        CloseHandle(hMutex);
    }
    CloseLogging();
    return (int)msg.wParam;
}
