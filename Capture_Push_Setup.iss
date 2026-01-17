; -- Capture_Push_Setup.iss --
; Capture_Push 安装脚本（内置Python环境，无需系统Python）

#define FileHandle FileOpen("VERSION")
#define AppVersion Trim(FileRead(FileHandle))
#expr FileClose(FileHandle)

[Setup]
AppId={{D8C9E6B5-F7A1-4B9D-8E2C-5A3D1C0B2A9E}}
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
AppMutex=Capture_PushTrayAppMutex
CloseApplications=yes
UsePreviousAppDir=yes
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
Source: "config.ini"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist uninsneveruninstall
Source: "config.ini"; DestDir: "{localappdata}\Capture_Push"; Flags: ignoreversion onlyifdoesntexist uninsneveruninstall

; 配置生成脚本
Source: "generate_config.py"; DestDir: "{app}"; Flags: ignoreversion

; C++托盘程序（需要预先编译）
Source: "tray\build\Release\Capture_Push_tray.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; 创建 AppData 目录
Name: "{localappdata}\Capture_Push"

[Icons]
Name: "{group}\Capture_Push托盘"; Filename: "{app}\Capture_Push_tray.exe"
Name: "{group}\配置工具"; Filename: "{app}\.venv\pythonw.exe"; Parameters: """{app}\gui\gui.py"""
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
; 1. 生成配置文件（直接利用随包分发的嵌入式 Python）
Filename: "{app}\.venv\python.exe"; Parameters: """{app}\generate_config.py"" ""{app}"""; StatusMsg: "Initializing config..."; Flags: runhidden waituntilterminated

; 安装后选项
Filename: "{app}\Capture_Push_tray.exe"; Description: "启动 Capture_Push 托盘程序"; Flags: nowait postinstall skipifsilent
Filename: "{app}\.venv\pythonw.exe"; Parameters: """{app}\gui\gui.py"""; Description: "打开配置工具"; Flags: nowait postinstall skipifsilent unchecked

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
var
  KeepConfig: Boolean;

// 卸载初始化
function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  // 询问是否保留配置
  if MsgBox('您是否要保留配置文件和日志？' + #13#10 + '(选择“否”将彻底删除所有数据)', mbConfirmation, MB_YESNO) = IDYES then
    KeepConfig := True
  else
    KeepConfig := False;

  // 尝试终止进程
  ShellExec('', 'taskkill.exe', '/f /im Capture_Push_tray.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

// 虚拟环境打包模式下，[Code] 段逻辑基本可以精简
function InitializeSetup(): Boolean;
var
  OldVersion: string;
begin
  Result := True;
  
  // 检查是否已经安装（通过注册表获取旧版本号）
  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{D8C9E6B5-F7A1-4B9D-8E2C-5A3D1C0B2A9E}_is1', 'DisplayVersion', OldVersion) then
  begin
    // 如果检测到旧版本
    if MsgBox('检测到系统已安装 Capture_Push (版本: ' + OldVersion + ')。' + #13#10 + #13#10 +
              '安装程序将更新核心程序文件，您的配置文件 (config.ini) 将会被保留。' + #13#10 + #13#10 +
              '是否继续更新？', mbInformation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end
  else
  begin
    // 首次安装提示
    MsgBox('欢迎使用 Capture_Push 安装程序' + #13#10 + #13#10 + 
           '✓ 预构建环境：Python 嵌入式环境已包含' + #13#10 +
           '✓ 即装即用：无需下载 Python 或安装依赖' + #13#10 +
           '✓ 环境隔离：不污染系统环境' + #13#10 + #13#10 + 
           '点击"下一步"开始解压安装', 
           mbInformation, MB_OK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataDir: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if not KeepConfig then
    begin
      AppDataDir := ExpandConstant('{localappdata}\Capture_Push');
      if DirExists(AppDataDir) then
      begin
        DelTree(AppDataDir, True, True, True);
      end;
    end;
  end;
end;