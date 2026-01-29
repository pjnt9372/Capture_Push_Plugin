#define NOMINMAX  // 修复：防止 Windows 头文件定义 min/max 宏干扰 std::min/max

#include <windows.h>
#include <shellapi.h>
#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <algorithm>  // for std::min and std::max
#include <chrono>     // for time logging
#include <mutex>      // for thread-safe logging
#include <iomanip>    // for std::put_time
#include <Shlobj.h>   // for SHGetKnownFolderPath
#include <tlhelp32.h> // for process enumeration
#include <wincrypt.h> // for DPAPI decryption

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "ole32.lib")  // for CoTaskMemFree
#pragma comment(lib, "advapi32.lib")  // for registry functions
#pragma comment(lib, "crypt32.lib")  // for DPAPI functions

#define IDI_ICON1 101
#define WM_TRAYICON (WM_USER + 1)
#define WM_LOOP_TIMER (WM_USER + 2)
#define ID_MENU_GRADE_CHANGED 1001
#define ID_MENU_GRADE_ALL 1002
#define ID_MENU_REFRESH_GRADE 1003
#define ID_MENU_SCHEDULE_TODAY 1004
#define ID_MENU_SCHEDULE_TOMORROW 1005
#define ID_MENU_SCHEDULE_FULL 1006
#define ID_MENU_REFRESH_SCHEDULE 1007
#define ID_MENU_SEND_CRASH_REPORT 1008
#define ID_MENU_CHECK_UPDATE 1009
#define ID_MENU_EXIT 1010
#define ID_MENU_OPEN_CONFIG 1011
#define TIMER_LOOP_CHECK 1001

// Define version and product name macros (fallback if not defined by CMake)
#ifndef APP_VERSION
#define APP_VERSION "0.0.0"  // Default fallback version
#endif

#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)

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

// 日志级别枚举
enum LogLevel {
    LOG_DEBUG,
    LOG_INFO,
    LOG_WARN,
    LOG_ERROR
};

// 全局日志级别，默认为INFO
LogLevel g_current_log_level = LOG_INFO;

// 函数前向声明
std::string GetInstallPathFromRegistry();
std::string GetExecutableDirectory();
std::string GetLogDirectory();
void ExecutePythonCommand(const std::string& command_suffix);
void ExecuteConfigGui();
void InitLogging();
void CloseLogging();
void LogMessage(const std::string& message, LogLevel level = LOG_INFO);
void CheckAndRotateLog(const std::string& logPath);

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

// 获取当前日期字符串 (YYYY-MM-DD)
std::string GetCurrentDateString() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
#ifdef _MSC_VER
    localtime_s(&tm, &time_t);
#else
    tm = *std::localtime(&time_t);
#endif
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%d");
    return oss.str();
}

// 清理旧日志，限制总大小为 50MB，并删除超过7天的日志
void CleanupOldLogs(const std::string& logDir) {
    const long long MAX_TOTAL_SIZE = 50 * 1024 * 1024; // 50MB
    const int MAX_DAYS = 7; // 最大保留天数
    std::string searchPath = logDir + "\\*.log*";
    
    struct LogFile {
        std::string path;
        unsigned long long size;
        unsigned long long lastWriteTime;
        SYSTEMTIME writeSysTime;
    };
    std::vector<LogFile> files;
    
    WIN32_FIND_DATAA findData;
    HANDLE hFind = FindFirstFileA(searchPath.c_str(), &findData);
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (!(findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                ULARGE_INTEGER fileSize;
                fileSize.LowPart = findData.nFileSizeLow;
                fileSize.HighPart = findData.nFileSizeHigh;
                
                ULARGE_INTEGER writeTime;
                writeTime.LowPart = findData.ftLastWriteTime.dwLowDateTime;
                writeTime.HighPart = findData.ftLastWriteTime.dwHighDateTime;
                
                // 将文件时间转换为系统时间
                FILETIME ft = {findData.ftLastWriteTime.dwLowDateTime, findData.ftLastWriteTime.dwHighDateTime};
                SYSTEMTIME st;
                FileTimeToSystemTime(&ft, &st);
                
                files.push_back({logDir + "\\" + findData.cFileName, fileSize.QuadPart, writeTime.QuadPart, st});
            }
        } while (FindNextFileA(hFind, &findData));
        FindClose(hFind);
    }
    
    // 获取当前时间
    SYSTEMTIME currentTime;
    GetLocalTime(&currentTime);
    
    // 计算7天前的日期
    SYSTEMTIME sevenDaysAgo = currentTime;
    // 先转换为 FILETIME，然后减去相应的时间量
    FILETIME ftCurrent, ftSevenDaysAgo;
    SystemTimeToFileTime(&currentTime, &ftCurrent);
    ULARGE_INTEGER uiCurrent, uiSevenDays;
    uiCurrent.LowPart = ftCurrent.dwLowDateTime;
    uiCurrent.HighPart = ftCurrent.dwHighDateTime;
    uiSevenDays.QuadPart = uiCurrent.QuadPart - (MAX_DAYS * 24 * 60 * 60 * 10000000ULL); // 7天的100纳秒间隔数
    ftSevenDaysAgo.dwLowDateTime = uiSevenDays.LowPart;
    ftSevenDaysAgo.dwHighDateTime = uiSevenDays.HighPart;
    
    // 按时间从旧到新排序
    std::sort(files.begin(), files.end(), [](const LogFile& a, const LogFile& b) {
        return a.lastWriteTime < b.lastWriteTime;
    });
    
    // 首先删除超过7天的日志文件
    for (auto it = files.begin(); it != files.end();) {
        FILETIME ftFile;
        SystemTimeToFileTime(&(it->writeSysTime), &ftFile);
        if (CompareFileTime(&ftFile, &ftSevenDaysAgo) < 0) { // 文件时间早于7天前
            if (DeleteFileA(it->path.c_str())) {
                LogMessage("已自动删除超过" + std::to_string(MAX_DAYS) + "天的日志: " + it->path, LOG_INFO);
                it = files.erase(it); // 从列表中移除已删除的文件
            } else {
                ++it; // 如果删除失败，移动到下一个
            }
        } else {
            ++it;
        }
    }
    
    // 对剩余文件按大小进行清理
    long long totalSize = 0;
    for (const auto& f : files) totalSize += f.size;
    
    size_t i = 0;
    while (totalSize > MAX_TOTAL_SIZE && i < files.size()) {
        if (DeleteFileA(files[i].path.c_str())) {
            totalSize -= files[i].size;
        }
        i++;
    }
}

// 初始化日志系统
void InitLogging() {
    std::string logDir = GetLogDirectory();
    if (logDir.empty()) return;
    
    // 1. 清理旧日志
    CleanupOldLogs(logDir);
    
    std::string dateStr = GetCurrentDateString();
    std::string logPath = logDir + "\\" + dateStr + "_tray.log";
    
    // 2. 检查当前文件大小（用于滚动）
    const long MAX_LOG_SIZE = 10 * 1024 * 1024; // 10MB
    std::ifstream file(logPath, std::ios::binary | std::ios::ate);
    if (file.is_open()) {
        long size = (long)file.tellg();
        file.close();
        if (size > MAX_LOG_SIZE) {
            // 简单滚动：直接重命名为 .old
            std::string oldLogPath = logPath + ".old";
            DeleteFileA(oldLogPath.c_str());
            MoveFileA(logPath.c_str(), oldLogPath.c_str());
        }
    }
    
    g_log_file.open(logPath, std::ios::out | std::ios::app);
    if (g_log_file.is_open()) {
        g_log_file << "\n--- Log session started at " 
                   << std::string(__DATE__) << " " << std::string(__TIME__);
        g_log_file << " | Version: " << APP_VERSION << " ---\n";
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

// 安全日志写入（带时间戳，仅写入文件）
void LogMessage(const std::string& message, LogLevel level) {
    // 检查是否为配置加载相关日志，如果是则不受全局日志级别影响
    bool is_config_load_message = (message.find("Reading config.ini from AppData") != std::string::npos ||
                                   message.find("Config loaded from AppData") != std::string::npos);
    
    // 根据全局日志级别过滤日志，但配置加载相关日志除外
    if (!is_config_load_message && level < g_current_log_level) {
        return; // 如果消息级别低于当前设置的最低级别，则不输出
    }
    
    // 获取日志级别字符串
    std::string levelStr;
    switch(level) {
        case LOG_DEBUG: levelStr = "DEBUG"; break;
        case LOG_WARN: levelStr = "WARN"; break;
        case LOG_ERROR: levelStr = "ERROR"; break;
        case LOG_INFO:
        default: levelStr = "INFO"; break;
    }

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
               << " - [TRAY] - " << levelStr << " - " << message; // 加入模块名标识
    std::string log_line = log_stream.str();

    // 写入日志文件
    if (g_log_file.is_open()) {
        std::lock_guard<std::mutex> lock(g_log_mutex);
        
        std::string logDir = GetLogDirectory();
        std::string dateStr = GetCurrentDateString();
        std::string logPath = logDir + "\\" + dateStr + "_tray.log";
        
        long current_pos = (long)g_log_file.tellp();
        const long MAX_LOG_SIZE = 10 * 1024 * 1024;
        
        if (current_pos > MAX_LOG_SIZE) {
            g_log_file.close();
            std::string oldLogPath = logPath + ".old";
            DeleteFileA(oldLogPath.c_str());
            MoveFileA(logPath.c_str(), oldLogPath.c_str());
            g_log_file.open(logPath, std::ios::out | std::ios::app);
            g_log_file << "--- Log rotated due to size limit ---\n";
        }

        g_log_file << log_line << '\n';
        g_log_file.flush();
    }
}

// 读取配置文件（从 AppData 目录）
void ReadLoopConfig() {
    LogMessage("Reading config.ini from AppData...", LOG_DEBUG);
    
    // 修复：从 AppData 目录读取配置文件
    std::string logDir = GetLogDirectory();
    if (logDir.empty()) {
        LogMessage("Failed to get AppData directory.", LOG_INFO);
        return;
    }
    std::string config_path = logDir + "\\config.ini";
    
    // 读取整个文件内容
    std::ifstream file(config_path, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        LogMessage("config.ini not found in AppData: " + config_path, LOG_INFO);
        return;
    }

    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);

    std::vector<char> buffer(size);
    if (size > 0) {
        if (!file.read(buffer.data(), size)) {
            LogMessage("Failed to read config file content.", LOG_ERROR);
            return;
        }
    }
    file.close();

    std::string config_content;
    
    // 尝试 DPAPI 解密
    if (size > 0) {
        DATA_BLOB data_in, data_out;
        data_in.pbData = (BYTE*)buffer.data();
        data_in.cbData = (DWORD)buffer.size();

        if (CryptUnprotectData(&data_in, NULL, NULL, NULL, NULL, 0, &data_out)) {
            config_content = std::string((char*)data_out.pbData, data_out.cbData);
            LocalFree(data_out.pbData);
            LogMessage("Config file decrypted using DPAPI.", LOG_DEBUG);
        } else {
            // 如果解密失败（可能是明文文件），直接作为 UTF-8 字符串
            config_content = std::string(buffer.begin(), buffer.end());
        }
    }

    std::istringstream config_stream(config_content);
    std::string line;
    std::string current_section;
    
    // 验证配置内容的基本格式
    if (config_content.empty()) {
        LogMessage("Warning: Config file is empty, using default settings.", LOG_WARN);
        return;
    }
    
    while (std::getline(config_stream, line)) {
        // 检查是否为有效的配置行
        if (line.length() > 1000) {  // 防止超长行
            LogMessage("Skipping overly long line in config file.", LOG_WARN);
            continue;
        }
        
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
            
            // 验证key和value长度
            if (key.length() > 100 || value.length() > 1000) {
                LogMessage("Warning: Skipping config entry with overly long key or value.", LOG_WARN);
                continue;
            }
            
            // 处理日志级别配置
            if (current_section == "logging") {
                if (key == "level") {
                    if (value == "DEBUG") {
                        g_current_log_level = LOG_DEBUG;
                        LogMessage("Log level set to DEBUG", LOG_DEBUG);
                    } else if (value == "INFO") {
                        g_current_log_level = LOG_INFO;
                        LogMessage("Log level set to INFO", LOG_DEBUG);
                    } else if (value == "WARN" || value == "WARNING") {
                        g_current_log_level = LOG_WARN;
                        LogMessage("Log level set to WARN", LOG_DEBUG);
                    } else if (value == "ERROR") {
                        g_current_log_level = LOG_ERROR;
                        LogMessage("Log level set to ERROR", LOG_DEBUG);
                    } else if (value == "CRITICAL") {
                        g_current_log_level = LOG_ERROR; // 映射到最高级别
                        LogMessage("Log level set to CRITICAL (mapped to ERROR)", LOG_DEBUG);
                    } else {
                        LogMessage("Unknown log level: " + value + ", keeping default INFO level", LOG_WARN);
                    }
                }
            } else if (current_section == "loop_getCourseGrades") {
                if (key == "enabled") {
                    try {
                        g_loop_config.grade_enabled = (value == "True" || value == "true" || value == "1");
                    } catch (...) {
                        LogMessage("Invalid value for grade_enabled, using default.", LOG_WARN);
                    }
                } else if (key == "time") {
                    try {
                        g_loop_config.grade_interval = std::stoi(value);
                        // 验证时间间隔的合理性（至少60秒）
                        if (g_loop_config.grade_interval < 60) {
                            g_loop_config.grade_interval = 60; // 最小值为60秒
                            LogMessage("Grade interval adjusted to minimum 60 seconds.", LOG_WARN);
                        }
                    } catch (...) {
                        LogMessage("Invalid value for grade time interval, using default.", LOG_WARN);
                    }
                }
            } else if (current_section == "loop_getCourseSchedule") {
                if (key == "enabled") {
                    try {
                        g_loop_config.schedule_enabled = (value == "True" || value == "true" || value == "1");
                    } catch (...) {
                        LogMessage("Invalid value for schedule_enabled, using default.", LOG_WARN);
                    }
                } else if (key == "time") {
                    try {
                        g_loop_config.schedule_interval = std::stoi(value);
                        // 验证时间间隔的合理性（至少60秒）
                        if (g_loop_config.schedule_interval < 60) {
                            g_loop_config.schedule_interval = 60; // 最小值为60秒
                            LogMessage("Schedule interval adjusted to minimum 60 seconds.", LOG_WARN);
                        }
                    } catch (...) {
                        LogMessage("Invalid value for schedule time interval, using default.", LOG_WARN);
                    }
                }
            } else if (current_section == "schedule_push") {
                if (key == "today_8am") {
                    try {
                        g_loop_config.push_today_8am = (value == "True" || value == "true" || value == "1");
                    } catch (...) {
                        LogMessage("Invalid value for today_8am, using default.", LOG_WARN);
                    }
                } else if (key == "tomorrow_9pm") {
                    try {
                        g_loop_config.push_tomorrow_9pm = (value == "True" || value == "true" || value == "1");
                    } catch (...) {
                        LogMessage("Invalid value for tomorrow_9pm, using default.", LOG_WARN);
                    }
                } else if (key == "next_week_sunday") {
                    try {
                        g_loop_config.push_next_week_sunday = (value == "True" || value == "true" || value == "1");
                    } catch (...) {
                        LogMessage("Invalid value for next_week_sunday, using default.", LOG_WARN);
                    }
                }
            }
        }
    }
    LogMessage("Config loaded from AppData: grade_enabled=" + std::to_string(g_loop_config.grade_enabled) +
               ", schedule_enabled=" + std::to_string(g_loop_config.schedule_enabled), LOG_DEBUG);
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
        LogMessage("Scheduled task: Today's schedule push (Triggered/Catch-up)", LOG_INFO);
        ExecutePythonCommand("--push-today");
        last_push_today_date = current_date;
    }

    // 前一天 21 点推送明天课表 (如果错过时间，在 21 点后至午夜前补发)
    if (g_loop_config.push_tomorrow_9pm && now_tm.tm_hour >= 21 && last_push_tomorrow_date != current_date) {
        LogMessage("Scheduled task: Tomorrow's schedule push (Triggered/Catch-up)", LOG_INFO);
        ExecutePythonCommand("--push-tomorrow");
        last_push_tomorrow_date = current_date;
    }

    // 周日 20 点推送下周全部课表 (如果周日 20 点后错过，则在周日内补发)
    if (g_loop_config.push_next_week_sunday && now_tm.tm_wday == 0 && now_tm.tm_hour >= 20 && last_push_next_week_date != current_date) {
        LogMessage("Scheduled task: Next week schedule push (Triggered/Catch-up)", LOG_INFO);
        ExecutePythonCommand("--push-next-week");
        last_push_next_week_date = current_date;
    }
}

// 执行循环检测
void ExecuteLoopCheck() {
    LogMessage("Timer triggered: performing checks.", LOG_INFO);
    
    // 每次触发都重新读取配置，确保能及时响应 GUI 的修改
    ReadLoopConfig();
    
    // 1. 检查定时推送
    ExecuteScheduledPushCheck();

    // 2. 检查循环刷新
    static time_t last_grade_check = 0;
    static time_t last_schedule_check = 0;
    time_t now = time(NULL);

    if (g_loop_config.grade_enabled && (now - last_grade_check >= g_loop_config.grade_interval)) {
        LogMessage("Grade loop: fetching grades.", LOG_INFO);
        ExecutePythonCommand("--fetch-grade");
        last_grade_check = now;
    }
    
    if (g_loop_config.schedule_enabled && (now - last_schedule_check >= g_loop_config.schedule_interval)) {
        LogMessage("Schedule loop: fetching schedule.", LOG_INFO);
        ExecutePythonCommand("--fetch-schedule");
        last_schedule_check = now;
    }
}

// 获取可执行文件所在目录（优先从注册表读取）
std::string GetExecutableDirectory() {
    // 优先尝试从注册表读取安装路径
    std::string registry_path = GetInstallPathFromRegistry();
    if (!registry_path.empty()) {
        LogMessage("从注册表获取到安装路径: " + registry_path, LOG_INFO);
        return registry_path;
    }
    
    // 如果注册表读取失败，回退到原来的方法
    LogMessage("注册表读取失败，使用可执行文件目录", LOG_INFO);
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
    std::string pythonw_path = exe_dir + "\\.venv\\pythonw.exe";
    std::string script_path = exe_dir + "\\core\\go.py";
    DWORD pythonw_attr = GetFileAttributesA(pythonw_path.c_str());
    DWORD script_attr = GetFileAttributesA(script_path.c_str());
    return (pythonw_attr != INVALID_FILE_ATTRIBUTES) && (script_attr != INVALID_FILE_ATTRIBUTES);
}

// 执行Python脚本（无窗口模式）
void ExecutePythonCommand(const std::string& command_suffix) {
    LogMessage("Executing Python command: " + command_suffix, LOG_INFO);
    if (!CheckPythonEnvironment()) {
        LogMessage("Python environment check failed!", LOG_INFO);
        MessageBoxA(NULL, "Python环境未正确安装！\n请重新运行安装程序。", "错误", MB_OK | MB_ICONERROR);
        return;
    }
    
    std::string exe_dir = GetExecutableDirectory();
    std::string pythonw_path = exe_dir + "\\.venv\\pythonw.exe";
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
        LogMessage("Python process started successfully.", LOG_INFO);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    } else {
        DWORD err = GetLastError();
        LogMessage("Failed to start Python process. Error: " + std::to_string(err), LOG_INFO);
    }
}

// 打开配置界面
void ExecuteConfigGui() {
    LogMessage("Launching config GUI...", LOG_INFO);
    std::string exe_dir = GetExecutableDirectory();
    std::string pythonw_path = exe_dir + "\\.venv\\pythonw.exe";
    std::string gui_script_path = exe_dir + "\\gui\\gui.py";

    if (GetFileAttributesA(pythonw_path.c_str()) == INVALID_FILE_ATTRIBUTES || 
        GetFileAttributesA(gui_script_path.c_str()) == INVALID_FILE_ATTRIBUTES) {
        LogMessage("Python environment or GUI script missing.", LOG_INFO);
        MessageBoxA(NULL, "配置界面所需环境未找到！\n请重新运行安装程序。", "错误", MB_OK | MB_ICONERROR);
        return;
    }

    // 使用 ShellExecuteA 启动 pythonw.exe 并传递 gui.py 路径
    std::string params = "\"" + gui_script_path + "\"";
    HINSTANCE result = ShellExecuteA(NULL, "open", pythonw_path.c_str(), params.c_str(), NULL, SW_SHOW);

    if ((intptr_t)result <= 32) {
        DWORD error = GetLastError();
        LogMessage("Failed to launch config GUI. Error: " + std::to_string(error), LOG_INFO);
        char error_msg[256];
        sprintf_s(error_msg, "无法启动配置工具！\n错误代码：%lu\n请检查程序文件是否完整。", error);
        MessageBoxA(NULL, error_msg, "错误", MB_OK | MB_ICONERROR);
    } else {
        LogMessage("Config GUI launched.", LOG_INFO);
    }
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
            
            wcscpy_s(nid.szTip, L"Capture_Push Tray");
            
            // 优先尝试从资源加载图标
            nid.hIcon = LoadIconW(GetModuleHandle(NULL), MAKEINTRESOURCEW(IDI_ICON1));
            
            if (nid.hIcon) {
                LogMessage("Successfully loaded icon from resources.", LOG_INFO);
            } else {
                // 如果资源加载失败，尝试从外部文件加载
                std::string exe_dir = GetExecutableDirectory();
                std::string icon_path = exe_dir + "\\resources\\app_icon.ico";
                
                HICON hCustomIcon = (HICON)LoadImageW(NULL, 
                    std::wstring(icon_path.begin(), icon_path.end()).c_str(), 
                    IMAGE_ICON, 
                    0, 
                    0, 
                    LR_LOADFROMFILE | LR_DEFAULTSIZE);
                
                if (hCustomIcon) {
                    nid.hIcon = hCustomIcon;
                    LogMessage("Successfully loaded custom tray icon from file: " + icon_path, LOG_INFO);
                } else {
                    // 如果自定义图标加载失败，使用默认图标
                    nid.hIcon = LoadIcon(NULL, IDI_APPLICATION);
                    LogMessage("Using default icon, failed to load from resources or file.", LOG_INFO);
                }
            }
            
            Shell_NotifyIconW(NIM_ADD, &nid);
            
            ReadLoopConfig();
            int interval = GetMinLoopInterval();
            if (interval > 0) {
                SetTimer(hwnd, TIMER_LOOP_CHECK, interval, NULL);
                LogMessage("Loop timer set to " + std::to_string(interval / 1000) + " seconds.", LOG_INFO);
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
                //AppendMenuW(hMenu, MF_SEPARATOR, 0, NULL);
                //AppendMenuW(hMenu, MF_STRING, ID_MENU_SEND_CRASH_REPORT, L"发送崩溃报告");
                //AppendMenuW(hMenu, MF_STRING, ID_MENU_CHECK_UPDATE, L"检查更新");
                AppendMenuW(hMenu, MF_SEPARATOR, 0, NULL);
                AppendMenuW(hMenu, MF_STRING, ID_MENU_OPEN_CONFIG, L"打开配置工具");
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
                    LogMessage("User selected: Push changed grades", LOG_INFO);
                    ExecutePythonCommand("--push-grade --force");
                    break;
                case ID_MENU_GRADE_ALL:
                    LogMessage("User selected: Push all grades", LOG_INFO);
                    ExecutePythonCommand("--push-all-grades --force");
                    break;
                case ID_MENU_REFRESH_GRADE:
                    LogMessage("User selected: Refresh grades", LOG_INFO);
                    ExecutePythonCommand("--fetch-grade --force");
                    break;
                case ID_MENU_SCHEDULE_TODAY:
                    LogMessage("User selected: Push today's schedule", LOG_INFO);
                    ExecutePythonCommand("--push-today --force");
                    break;
                case ID_MENU_SCHEDULE_TOMORROW:
                    LogMessage("User selected: Push tomorrow's schedule", LOG_INFO);
                    ExecutePythonCommand("--push-tomorrow --force");
                    break;
                case ID_MENU_SCHEDULE_FULL:
                    LogMessage("User selected: Push full semester schedule", LOG_INFO);
                    ExecutePythonCommand("--push-full-schedule --force");
                    break;
                /*case ID_MENU_SEND_CRASH_REPORT:
                    LogMessage("User selected: Send crash report", LOG_INFO);
                    ExecutePythonCommand("--pack-logs");
                    break;
                case ID_MENU_CHECK_UPDATE:
                    LogMessage("User selected: Check for updates", LOG_INFO);
                    ExecutePythonCommand("--check-update");
                    break;*/
                case ID_MENU_REFRESH_SCHEDULE:
                    LogMessage("User selected: Refresh schedule", LOG_INFO);
                    ExecutePythonCommand("--fetch-schedule --force");
                    break;
                case ID_MENU_OPEN_CONFIG:
                    ExecuteConfigGui();
                    break;
                case ID_MENU_EXIT:
                    LogMessage("User selected 'Exit'. Shutting down.", LOG_INFO);
                    KillTimer(hwnd, TIMER_LOOP_CHECK);
                    Shell_NotifyIconW(NIM_DELETE, &nid);
                    PostQuitMessage(0);
                    break;
            }
            break;
        }
            
        case WM_DESTROY:
        {
            KillTimer(hwnd, TIMER_LOOP_CHECK);
            Shell_NotifyIconW(NIM_DELETE, &nid);
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
    // 在应用程序启动时读取配置以设置日志级别
    ReadLoopConfig();
    LogMessage("Application starting...", LOG_INFO);
    LogMessage("Built with version: " + std::string(APP_VERSION), LOG_INFO);

    // 双重检查：互斥锁 + 进程列表检查
    HANDLE hMutex = CreateMutexW(NULL, TRUE, L"Capture_PushTrayAppMutex");
    bool alreadyRunning = (GetLastError() == ERROR_ALREADY_EXISTS);
    
    if (alreadyRunning || IsProcessRunning(L"Capture_Push_tray.exe")) {
        LogMessage("Another instance is already running. Exiting.", LOG_INFO);
        MessageBoxW(NULL, 
                    L"Capture_Push Tray Program is already running!\nIf you can't see the tray icon, please check Task Manager.",
                    L"Info",
                    MB_OK | MB_ICONINFORMATION);
        if (hMutex) CloseHandle(hMutex);
        CloseLogging();
        return 0;
    }
    
    const wchar_t CLASS_NAME[] = L"TrayAppClass";
    WNDCLASSW wc = {};
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hIcon = LoadIconW(hInstance, MAKEINTRESOURCEW(IDI_ICON1));
    wc.lpszClassName = CLASS_NAME;
    RegisterClassW(&wc);
    
    hwnd = CreateWindowExW(0, CLASS_NAME, L"Capture_Push Tray Program",
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