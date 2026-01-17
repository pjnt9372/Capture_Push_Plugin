; -- Capture_Push_Setup.iss --
; Capture_Push 安装脚本（内置Python环境，无需系统Python）

#define FileHandle FileOpen("VERSION")
#define AppVersion Trim(FileRead(FileHandle))
#expr FileClose(FileHandle)

[Setup]
AppName=Capture_Push
AppVersion={#AppVersion}
AppPublisher=pjnt9372
DefaultDirName={autopf}\Capture_Push
DefaultGroupName=Capture_Push
OutputDir=Output
OutputBaseFilename=Capture_Push_Setup
Compression=lzma2/normal
SolidCompression=yes
InternalCompressLevel=normal
PrivilegesRequired=admin
WizardStyle=modern
SetupIconFile=
UninstallDisplayIcon={app}\Capture_Push_tray.exe

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Files]
; 直接打包预构建好的虚拟环境
Source: ".venv\*"; DestDir: "{app}\.venv"; Flags: ignoreversion recursesubdirs

; Python脚本和配置
Source: "core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs
Source: "gui\*"; DestDir: "{app}\gui"; Flags: ignoreversion recursesubdirs
Source: "VERSION"; DestDir: "{app}"; Flags: ignoreversion

; 院校模块
Source: "core\school\*"; DestDir: "{app}\core\school"; Flags: ignoreversion recursesubdirs

; 配置文件 - 同时释放到程序目录和 AppData 目录
Source: "config.ini"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.ini"; DestDir: "{localappdata}\Capture_Push"; Flags: ignoreversion

; 配置生成脚本
Source: "generate_config.py"; DestDir: "{app}"; Flags: ignoreversion

; C++托盘程序（需要预先编译）
Source: "tray\build\Release\Capture_Push_tray.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; 创建 AppData 目录
Name: "{localappdata}\Capture_Push"

[Icons]
Name: "{group}\Capture_Push托盘"; Filename: "{app}\Capture_Push_tray.exe"
Name: "{group}\配置工具"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\gui\gui.py"""
Name: "{group}\查看配置信息"; Filename: "{app}\install_config.txt"
Name: "{group}\卸载Capture_Push"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Capture_Push"; Filename: "{app}\Capture_Push_tray.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"
Name: autostart; Description: "开机自动启动托盘程序"; GroupDescription: "附加选项:"

[Registry]
; 注册安装路径
Root: HKLM; Subkey: "SOFTWARE\Capture_Push"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue

; 自启动托盘程序（如果用户选择了autostart任务）
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Capture_Push_Tray"; ValueData: """{app}\Capture_Push_tray.exe"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; 1. 生成配置文件（直接利用随包分发的虚拟环境）
Filename: "{app}\.venv\Scripts\python.exe"; Parameters: """{app}\generate_config.py"" ""{app}"" "; StatusMsg: "Initializing config..."; Flags: runhidden waituntilterminated

; 安装后选项
Filename: "{app}\Capture_Push_tray.exe"; Description: "启动 Capture_Push 托盘程序"; Flags: nowait postinstall skipifsilent
Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\gui\gui.py"""; Description: "打开配置工具"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
; 清理程序目录
Type: filesandordirs; Name: "{app}\.venv"
Type: files; Name: "{app}\install_config.txt"
Type: files; Name: "{app}\app.log"
Type: filesandordirs; Name: "{app}\core\state"
Type: filesandordirs; Name: "{app}\core\__pycache__"
Type: filesandordirs; Name: "{app}\gui\__pycache__"
; 清理 AppData 目录中的日志文件（保留配置文件让用户自行删除）
Type: files; Name: "{localappdata}\Capture_Push\*.log"

[Code]
// 虚拟环境打包模式下，[Code] 段逻辑基本可以精简
function InitializeSetup(): Boolean;
begin
  Result := True;
  MsgBox('Capture_Push 安装程序' + #13#10 + #13#10 + 
         '✓ 预构建环境：Python 虚拟环境已包含' + #13#10 +
         '✓ 即装即用：无需下载 Python 或安装依赖' + #13#10 +
         '✓ 环境隔离：不污染系统环境' + #13#10 + #13#10 + 
         '点击"下一步"开始解压安装', 
         mbInformation, MB_OK);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  // 卸载时只需正常删除目录即可，因为虚拟环境是作为普通文件安装的
end;
