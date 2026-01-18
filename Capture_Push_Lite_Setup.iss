; -- Capture_Push_Lite_Setup.iss --
; Capture_Push 轻量级更新包（仅更新程序文件，不包含Python环境）

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
OutputBaseFilename=Capture_Push_Lite_Setup
Compression=lzma2/ultra64
SolidCompression=yes
InternalCompressLevel=ultra64
PrivilegesRequired=admin
WizardStyle=modern
AppMutex=Capture_PushTrayAppMutex
ArchitecturesInstallIn64BitMode=x64
CloseApplications=yes
UsePreviousAppDir=yes
SetupIconFile=
UninstallDisplayIcon={app}\Capture_Push_tray.exe
DisableProgramGroupPage=yes
DisableWelcomePage=no

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Files]
; 仅打包核心程序文件，不包含 .venv
; Python脚本和配置
Source: "core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs
Source: "gui\*"; DestDir: "{app}\gui"; Flags: ignoreversion recursesubdirs
Source: "VERSION"; DestDir: "{app}"; Flags: ignoreversion

; 配置文件 - 释放到 AppData 目录（但不覆盖已存在的）
Source: "config.ini"; DestDir: "{localappdata}\Capture_Push"; Flags: ignoreversion onlyifdoesntexist uninsneveruninstall

; 配置生成脚本
Source: "generate_config.py"; DestDir: "{app}"; Flags: ignoreversion

; C++托盘程序
Source: "tray\build\Release\Capture_Push_tray.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; 创建 AppData 目录
Name: "{localappdata}\Capture_Push"

[Registry]
; 注册安装路径
Root: HKLM64; Subkey: "SOFTWARE\Capture_Push"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue

; 自启动托盘程序保持不变
Root: HKLM64; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Capture_Push_Tray"; ValueData: """{app}\Capture_Push_tray.exe"""; Flags: uninsdeletevalue dontcreatekey reg64

[Run]
; 自动重新启动托盘程序（仅针对静默安装/自动更新场景）
Filename: "{app}\Capture_Push_tray.exe"; Flags: nowait; Check: WizardSilent

; 安装后选项（针对普通交互式安装场景）
Filename: "{app}\Capture_Push_tray.exe"; Description: "启动 Capture_Push 托盘程序"; Flags: nowait postinstall skipifsilent
Filename: "{app}\.venv\pythonw.exe"; Parameters: """{app}\gui\gui.py"""; Description: "打开配置工具"; Flags: nowait postinstall skipifsilent unchecked

[Code]
var
  PythonEnvExists: Boolean;

// 检查是否已安装完整版（含Python环境）
function CheckPythonEnvironment(): Boolean;
var
  InstallPath: string;
  PythonExe: string;
begin
  Result := False;
  
  // 从注册表读取安装路径
  if RegQueryStringValue(HKLM64, 'SOFTWARE\Capture_Push', 'InstallPath', InstallPath) then
  begin
    PythonExe := AddBackslash(InstallPath) + '.venv\python.exe';
    if FileExists(PythonExe) then
      Result := True;
  end;
end;

function InitializeSetup(): Boolean;
var
  OldVersion: string;
  ResultCode: Integer;
begin
  Result := True;
  
  // 主动关闭运行中的托盘程序（升级场景）
  ShellExec('', 'taskkill.exe', '/f /im Capture_Push_tray.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  // 检查Python环境是否存在
  PythonEnvExists := CheckPythonEnvironment();
  
  // 检查是否已经安装
  if RegQueryStringValue(HKLM64, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{D8C9E6B5-F7A1-4B9D-8E2C-5A3D1C0B2A9E}_is1', 'DisplayVersion', OldVersion) then
  begin
    if not PythonEnvExists then
    begin
      // 如果已安装但没有Python环境，提示用户
      if MsgBox('检测到系统中的 Capture_Push 缺少 Python 运行环境。' + #13#10 + #13#10 +
                '轻量级更新包仅用于升级已完整安装的版本。' + #13#10 +
                '请先下载并安装完整版安装包。' + #13#10 + #13#10 +
                '是否继续安装？（可能导致程序无法运行）', mbError, MB_YESNO) = IDNO then
      begin
        Result := False;
        Exit;
      end;
    end
    else
    begin
      // 正常更新流程
      if MsgBox('检测到已安装 Capture_Push (版本: ' + OldVersion + ')。' + #13#10 + #13#10 +
                '此轻量级更新包将更新核心程序文件。' + #13#10 +
                '您的配置文件和 Python 环境将会被保留。' + #13#10 + #13#10 +
                '是否继续更新？', mbInformation, MB_YESNO) = IDNO then
      begin
        Result := False;
      end;
    end;
  end
  else
  begin
    // 首次安装提示（不推荐使用轻量版首次安装）
    if MsgBox('您正在使用轻量级更新包。' + #13#10 + #13#10 +
              '此安装包不包含 Python 运行环境，仅适用于已安装完整版的升级。' + #13#10 + #13#10 +
              '如果这是首次安装，请下载完整版安装包。' + #13#10 + #13#10 +
              '是否继续？', mbError, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end;
end;
