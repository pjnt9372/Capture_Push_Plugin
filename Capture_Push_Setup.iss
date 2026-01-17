; -- Capture_Push_Setup.iss --
; Capture_Push 安装脚本（内置Python环境，无需系统Python）

[Setup]
AppName=Capture_Push
AppVersion=0.2.0_Dev
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
; Python 3.11.9 安装包（需提前下载到项目根目录）
Source: "python-3.11.9-amd64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

; 环境安装器脚本
Source: "installer.py"; DestDir: "{app}"; Flags: ignoreversion

; Python 依赖列表
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; Python脚本和配置
Source: "core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs
Source: "gui\*"; DestDir: "{app}\gui"; Flags: ignoreversion recursesubdirs

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
; 1. 检测并安装 Python（仅在不存在时）- 显示安装界面让用户确认
Filename: "{tmp}\python-3.11.9-amd64.exe"; Parameters: "InstallAllUsers=0 TargetDir=""{app}\python"" PrependPath=0 Include_test=0 Include_tcltk=0"; StatusMsg: "正在安装 Python 3.11.9..."; Flags: waituntilterminated; Check: NeedInstallPython; AfterInstall: AfterPythonInstallWithResult

; 2. 运行环境安装器脚本创建虚拟环境（直接使用内置 Python 运行）
Filename: "{app}\python\python.exe"; Parameters: """{app}\installer.py"" ""{app}"""; StatusMsg: "正在配置虚拟环境并安装依赖..."; Flags: waituntilterminated; Check: CheckPythonReady

; 3. 生成配置文件（仅在虚拟环境创建成功后）
Filename: "{app}\.venv\Scripts\python.exe"; Parameters: """{app}\generate_config.py"" ""{app}"""; StatusMsg: "正在生成配置信息..."; Flags: runhidden waituntilterminated; Check: CheckVenvReady

; 安装后选项
Filename: "{app}\Capture_Push_tray.exe"; Description: "启动 Capture_Push 托盘程序"; Flags: nowait postinstall skipifsilent
Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\gui\gui.py"""; Description: "打开配置工具"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
; 清理程序目录
Type: filesandordirs; Name: "{app}\.venv"
Type: files; Name: "{app}\installer.py"
Type: files; Name: "{app}\requirements.txt"
Type: files; Name: "{app}\install_config.txt"
Type: files; Name: "{app}\app.log"
Type: filesandordirs; Name: "{app}\core\state"
Type: filesandordirs; Name: "{app}\core\__pycache__"
Type: filesandordirs; Name: "{app}\gui\__pycache__"
; 清理 AppData 目录中的日志文件（保留配置文件让用户自行删除）
Type: files; Name: "{localappdata}\Capture_Push\*.log"

[Code]
// 全局变量：记录是否需要安装 Python
var
  g_NeedInstallPython: Boolean;
  g_PythonInstalled: Boolean;

// 检查 Python 是否已存在
function CheckPythonExists(): Boolean;
var
  PythonExePath: String;
begin
  PythonExePath := ExpandConstant('{app}\python\python.exe');
  Result := FileExists(PythonExePath);
end;

// 检查是否需要安装 Python
function NeedInstallPython(): Boolean;
begin
  Result := g_NeedInstallPython;
end;

// 验证 Python 是否安装成功
function VerifyPythonInstallation(): Boolean;
var
  PythonExePath: String;
  ResultCode: Integer;
  RetryCount: Integer;
begin
  Result := False;
  PythonExePath := ExpandConstant('{app}\python\python.exe');
  
  Log('Verifying Python installation...');
  
  // 检查 python.exe 是否存在（等待文件系统同步，最多重试 3 次）
  RetryCount := 0;
  while (RetryCount < 3) and (not FileExists(PythonExePath)) do
  begin
    Log('Retry ' + IntToStr(RetryCount + 1) + ': Waiting for python.exe...');
    Sleep(500);
    RetryCount := RetryCount + 1;
  end;
  
  if not FileExists(PythonExePath) then
  begin
    Log('ERROR: Python installation failed - python.exe not found at: ' + PythonExePath);
    MsgBox('Python 安装失败！' + #13#10 + #13#10 +
           '找不到 python.exe，安装无法继续。' + #13#10 +
           '安装程序可能未正确执行。' + #13#10 +
           '请重新运行安装程序。',
           mbError, MB_OK);
    Exit;
  end;
  
  Log('python.exe found at: ' + PythonExePath);
  
  // 尝试执行 python --version 验证
  if Exec(PythonExePath, '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      Log('Python installation verified successfully.');
      Result := True;
    end
    else
    begin
      Log('ERROR: Python verification failed with exit code: ' + IntToStr(ResultCode));
      MsgBox('Python 安装验证失败！' + #13#10 + #13#10 +
             '退出代码: ' + IntToStr(ResultCode) + #13#10 +
             '请重新运行安装程序。',
             mbError, MB_OK);
    end;
  end
  else
  begin
    Log('ERROR: Failed to execute Python for verification.');
    MsgBox('Python 验证失败！' + #13#10 + #13#10 +
           '无法执行 Python，安装无法继续。' + #13#10 +
           '请重新运行安装程序。',
           mbError, MB_OK);
  end;
end;

// 从注册表中获取 Python 的卸载命令
function GetPythonUninstallString(var UninstallString: String): Boolean;
var
  SubkeyNames: TArrayOfString;
  I: Integer;
  InstallLoc: String;
  TargetDir: String;
  KeyPath: String;
begin
  Result := False;
  TargetDir := Uppercase(ExpandConstant('{app}\python'));
  // 去除末尾斜杠
  if Copy(TargetDir, Length(TargetDir), 1) = '\' then
    TargetDir := Copy(TargetDir, 1, Length(TargetDir) - 1);

  KeyPath := 'Software\Microsoft\Windows\CurrentVersion\Uninstall';
  
  // 遍历当前用户的卸载列表（因为我们安装时用了 InstallAllUsers=0）
  if RegGetSubkeyNames(HKEY_CURRENT_USER, KeyPath, SubkeyNames) then
  begin
    for I := 0 to GetArrayLength(SubkeyNames) - 1 do
    begin
      if RegQueryStringValue(HKEY_CURRENT_USER, KeyPath + '\' + SubkeyNames[I], 'InstallLocation', InstallLoc) then
      begin
        InstallLoc := Uppercase(InstallLoc);
        if Copy(InstallLoc, Length(InstallLoc), 1) = '\' then
          InstallLoc := Copy(InstallLoc, 1, Length(InstallLoc) - 1);

        // 如果安装路径匹配，则提取卸载命令
        if InstallLoc = TargetDir then
        begin
          if RegQueryStringValue(HKEY_CURRENT_USER, KeyPath + '\' + SubkeyNames[I], 'UninstallString', UninstallString) then
          begin
            Result := True;
            Break;
          end;
        end;
      end;
    end;
  end;
end;

// Python 安装后的回调函数（带返回值检查）
procedure AfterPythonInstallWithResult();
var
  PythonInstallerPath: String;
begin
  PythonInstallerPath := ExpandConstant('{tmp}\python-3.11.9-amd64.exe');
  Log('Python installer execution completed.');
  
  // 注意：Python 安装程序已经执行完毕（waituntilterminated）
  // 但 Inno Setup 的 AfterInstall 回调无法直接获取返回码
  // 所以我们通过验证文件是否存在来判断安装是否成功
  
  g_PythonInstalled := VerifyPythonInstallation();
  if not g_PythonInstalled then
  begin
    Log('CRITICAL: Python installation failed verification!');
  end
  else
  begin
    Log('Python installation and verification successful.');
  end;
end;

// 检查 Python 是否就绪（用于后续步骤的前置条件）
function CheckPythonReady(): Boolean;
begin
  Result := g_PythonInstalled;
  if not Result then
  begin
    Log('ERROR: Cannot proceed - Python is not ready.');
    MsgBox('Python 环境未就绪！' + #13#10 + #13#10 +
           '无法继续安装虚拟环境。' + #13#10 +
           '请检查安装日志并重试。',
           mbError, MB_OK);
  end;
end;

// 检查虚拟环境是否就绪
function CheckVenvReady(): Boolean;
var
  VenvPython: String;
begin
  VenvPython := ExpandConstant('{app}\.venv\Scripts\python.exe');
  Result := FileExists(VenvPython);
  if not Result then
  begin
    Log('ERROR: Virtual environment not found at: ' + VenvPython);
  end;
end;

// 初始化安装
function InitializeSetup(): Boolean;
begin
  Result := True;
  
  // 显示欢迎信息
  MsgBox('Capture_Push 安装程序' + #13#10 + #13#10 + 
         '✓ 内置Python环境：Python 3.11.9' + #13#10 +
         '✓ 安装位置：软件同一目录' + #13#10 +
         '✓ 环境隔离：不污染系统环境' + #13#10 +
         '✓ 安装大小：约 1500 MB' + #13#10 + #13#10 + 
         '点击"下一步"继续安装', 
         mbInformation, MB_OK);
end;

// 安装完成后的处理
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    // 在安装开始前检测 Python 是否存在
    if CheckPythonExists() then
    begin
      g_NeedInstallPython := False;
      g_PythonInstalled := True;
      Log('Python already exists, skip installation.');
    end
    else
    begin
      g_NeedInstallPython := True;
      g_PythonInstalled := False;
      Log('Python not found, will install to: ' + ExpandConstant('{app}\python'));
      MsgBox('未检测到 Python 环境' + #13#10 + #13#10 +
             '接下来将弹出 Python 安装程序，请按照以下设置安装：' + #13#10 + #13#10 +
             '• 安装目录：' + ExpandConstant('{app}\python') + #13#10 +
             '• 不要添加到 PATH（已默认设置）' + #13#10 +
             '• 点击 "Install" 开始安装' + #13#10 + #13#10 +
             '安装完成后，Capture_Push 安装将继续。',
             mbInformation, MB_OK);
    end;
  end;
  
  if CurStep = ssPostInstall then
  begin
    // 这里可以添加额外的安装后处理
    if g_PythonInstalled then
    begin
      Log('Installation completed successfully with Python ready.');
    end
    else
    begin
      Log('WARNING: Installation completed but Python status is uncertain.');
    end;
  end;
end;

// 卸载前的清理
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  PythonDir, UninstallCmd, Parameters: String;
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    // 1. 询问用户是否卸载内置 Python
    PythonDir := ExpandConstant('{app}\python');
    if DirExists(PythonDir) then
    begin
      if MsgBox('是否卸载内置的 Python 3.11.9 环境？' + #13#10 + #13#10 +
                '选择“是”：将启动 Python 官方卸载程序（推荐）。' + #13#10 +
                '选择“否”：保留 Python 文件夹。', 
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        if GetPythonUninstallString(UninstallCmd) then
        begin
          Log('Found Python uninstaller: ' + UninstallCmd);
          
          // 这里的 UninstallCmd 通常包含路径和可能的参数
          // 如果 UninstallCmd 包含引号，需要妥善处理
          if Copy(UninstallCmd, 1, 1) = '"' then
          begin
            // 假设格式为 "C:\path\to\exe" /uninstall
            // 实际上 Python Bundle 的 UninstallString 往往就是 exe 路径本身
            // 我们尝试直接执行它并附加 /uninstall 参数
          end;
          
          // 提示用户
          MsgBox('即将启动 Python 官方卸载程序，请在弹出窗口中点击 "Uninstall" 完成清理。', mbInformation, MB_OK);
          
          // 执行卸载。不带 /quiet 以便用户看到进度并确保清理干净。
          // 注意：UninstallCmd 可能是 "C:\...\Setup.exe" /uninstall
          if not Exec('cmd.exe', '/c ' + UninstallCmd, '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
          begin
            MsgBox('无法启动 Python 卸载程序，请手动在控制面板卸载。', mbError, MB_OK);
          end;
        end
        else
        begin
          MsgBox('未在注册表中找到 Python 卸载信息。' + #13#10 + #13#10 +
                 '为避免系统环境损坏，安装程序不会强行删除文件夹。' + #13#10 +
                 '请在卸载完成后手动检查或通过控制面板清理。', mbInformation, MB_OK);
        end;
      end;
    end;
  end;
end;
