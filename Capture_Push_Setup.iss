; -- Capture_Push_Setup.iss --
; Capture_Push 安装脚本（内置Python环境，无需系统Python）
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
OutputBaseFilename=Capture_Push_Setup
Compression=lzma2/normal
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern
AppMutex=Capture_PushTrayAppMutex
ArchitecturesInstallIn64BitMode=x64
CloseApplications=yes
UsePreviousAppDir=yes
UninstallDisplayIcon={app}\Capture_Push_tray.exe
ChangesAssociations=yes
MinVersion=6.1

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: desktopicon; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"; Check: CheckDesktopTask
Name: autostart; Description: "开机自动启动托盘程序"; GroupDescription: "附加选项:"; Check: CheckAutostartTask

[Files]
Source: ".venv\*"; DestDir: "{app}\.venv"; Flags: ignoreversion recursesubdirs
Source: "core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs excludeitchildless
Source: "core\school\12345\*"; DestDir: "{app}\core\school\12345"; Flags: ignoreversion recursesubdirs
Source: "core\plugins\school\12345\*"; DestDir: "{app}\core\plugins\school\12345"; Flags: ignoreversion recursesubdirs
Source: "gui\*"; DestDir: "{app}\gui"; Flags: ignoreversion recursesubdirs
Source: "resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs
Source: "VERSION"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.ini"; DestDir: "{localappdata}\Capture_Push"; Flags: ignoreversion onlyifdoesntexist uninsneveruninstall
Source: "generate_config.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "tray\build\Release\Capture_Push_tray.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Capture_Push托盘"; Filename: "{app}\Capture_Push_tray.exe"
Name: "{group}\配置工具"; Filename: "{app}\.venv\pythonw.exe"; Parameters: """{app}\gui\gui.py"""
Name: "{group}\卸载Capture_Push"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Capture_Push"; Filename: "{app}\Capture_Push_tray.exe"; Tasks: desktopicon

[Registry]
Root: HKLM64; Subkey: "SOFTWARE\Capture_Push"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue
Root: HKCU64; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Capture_Push_Tray"; ValueData: """{app}\Capture_Push_tray.exe"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\.venv\python.exe"; Parameters: """{app}\generate_config.py"" ""{app}"""; StatusMsg: "Initializing config..."; Flags: runhidden waituntilterminated
Filename: "{app}\Capture_Push_tray.exe"; Flags: nowait postinstall skipifsilent; Description: "启动 Capture_Push 托盘程序"
Filename: "{app}\.venv\pythonw.exe"; Parameters: """{app}\gui\gui.py"""; Description: "打开配置工具"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.venv"
Type: files; Name: "{app}\app.log"
Type: filesandordirs; Name: "{app}\core\state"
Type: filesandordirs; Name: "{app}\core\__pycache__"
Type: filesandordirs; Name: "{app}\gui\__pycache__"
Type: files; Name: "{localappdata}\Capture_Push\*.log"

[Code]
var
  KeepConfig: Boolean;

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

function InitializeSetup(): Boolean;
var
  OldVersion: string;
  ResultCode: Integer;
begin
  Result := True;
  ShellExec('', 'taskkill.exe', '/f /im Capture_Push_tray.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  if RegQueryStringValue(HKLM64, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{D8C9E6B5-F7A1-4B9D-8E2C-5A3D1C0B2A9E}_is1', 'DisplayVersion', OldVersion) then
  begin
    if not WizardSilent then
    begin
      if MsgBox('检测到已安装版本 ' + OldVersion + '。是否继续更新？', mbInformation, MB_YESNO) = IDNO then
        Result := False;
    end;
  end;
end;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  KeepConfig := (MsgBox('是否保留配置文件和日志？', mbConfirmation, MB_YESNO) = IDYES);
  ShellExec('', 'taskkill.exe', '/f /im Capture_Push_tray.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and (not KeepConfig) then
  begin
    DelTree(ExpandConstant('{localappdata}\Capture_Push'), True, True, True);
  end;
end;
