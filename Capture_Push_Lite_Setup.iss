; -- Capture_Push_Lite_Setup.iss --
; Capture_Push 轻量级更新包（仅更新程序文件，不包含Python环境）
;
; 支持的命令行参数:
; /SILENT - 静默安装
; /VERYSILENT - 完全静默安装
; /DIR="x:" - 指定安装目录
; /DESKTOPON="yes" - 强制创建桌面图标
; /DESKTOPOFF="yes" - 强制不创建桌面图标
; /AUTOSTARTON="yes" - 强制开启开机自启
; /AUTOSTARTOFF="yes" - 强制关闭开机自启

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
UninstallDisplayIcon={app}\Capture_Push_tray.exe
DisableProgramGroupPage=yes
DisableWelcomePage=no
ChangesAssociations=yes
MinVersion=6.1

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: desktopicon; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"; Check: CheckDesktopTask
Name: autostart; Description: "开机自动启动托盘程序"; GroupDescription: "附加选项:"; Check: CheckAutostartTask

[Files]
; 仅打包核心程序文件，不包含 .venv
Source: "core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs excludeitchildless
Source: "core\school\12345\*"; DestDir: "{app}\core\school\12345"; Flags: ignoreversion recursesubdirs
Source: "core\plugins\school\12345\*"; DestDir: "{app}\core\plugins\school\12345"; Flags: ignoreversion recursesubdirs
Source: "gui\*"; DestDir: "{app}\gui"; Flags: ignoreversion recursesubdirs
Source: "resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs
Source: "VERSION"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.ini"; DestDir: "{localappdata}\Capture_Push"; Flags: ignoreversion onlyifdoesntexist uninsneveruninstall
Source: "generate_config.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "tray\build\Release\Capture_Push_tray.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{localappdata}\Capture_Push"

[Registry]
Root: HKLM64; Subkey: "SOFTWARE\Capture_Push"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue
Root: HKCU64; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Capture_Push_Tray"; ValueData: """{app}\Capture_Push_tray.exe"""; Flags: uninsdeletevalue dontcreatekey; Tasks: autostart

[Run]
Filename: "{app}\Capture_Push_tray.exe"; Flags: nowait postinstall ; Description: "启动 Capture_Push 托盘程序"

[Code]
var
  PythonEnvExists: Boolean;

// 检查命令行参数
function IsCmdLineParam(ParamName: string): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
  begin
    if CompareText(ParamStr(I), '/' + ParamName) = 0 then
    begin
      Result := True;
      Break;
    end;
  end;
end;

function GetCmdLineParamValue(ParamName: string): string;
var
  I: Integer;
  P, V: string;
begin
  Result := '';
  for I := 1 to ParamCount do
  begin
    P := ParamStr(I);
    if Pos('/' + UpperCase(ParamName) + '=', UpperCase(P)) = 1 then
    begin
      V := P;
      Delete(V, 1, Length(ParamName) + 2);
      if (Length(V) >= 2) and (V[1] = '"') and (V[Length(V)] = '"') then
        V := Copy(V, 2, Length(V) - 2);
      Result := V;
      Break;
    end;
  end;
end;

// Task Check 函数
function CheckDesktopTask(): Boolean;
begin
  Result := True; // 默认开启
  if IsCmdLineParam('DESKTOPOFF') then Result := False
  else if IsCmdLineParam('DESKTOPON') then Result := True;
end;

function CheckAutostartTask(): Boolean;
begin
  Result := True; // 默认开启
  if IsCmdLineParam('AUTOSTARTOFF') then Result := False
  else if IsCmdLineParam('AUTOSTARTON') then Result := True;
end;

// 检查是否已安装完整版（含Python环境）
function CheckPythonEnvironment(): Boolean;
var
  InstallPath: string;
  PythonExe: string;
begin
  Result := False;
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
  ShellExec('', 'taskkill.exe', '/f /im Capture_Push_tray.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  PythonEnvExists := CheckPythonEnvironment();
  
  if RegQueryStringValue(HKLM64, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{D8C9E6B5-F7A1-4B9D-8E2C-5A3D1C0B2A9E}_is1', 'DisplayVersion', OldVersion) then
  begin
    if not WizardSilent then
    begin
      if not PythonEnvExists then
      begin
        if MsgBox('检测到系统中缺少 Python 运行环境。轻量更新包可能无法运行。是否继续？', mbError, MB_YESNO) = IDNO then
        begin
          Result := False;
          Exit;
        end;
      end;
      
      if MsgBox('检测到已安装版本 ' + OldVersion + '。是否继续更新？', mbInformation, MB_YESNO) = IDNO then
        Result := False;
    end;
  end
  else
  begin
    if not WizardSilent then
    begin
      if MsgBox('这是轻量级更新包，不包含 Python 环境。建议首次安装使用完整版。是否继续？', mbError, MB_YESNO) = IDNO then
        Result := False;
    end;
  end;
end;
