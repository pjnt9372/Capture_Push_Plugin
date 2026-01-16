; -- Capture_Push_Setup.iss --
; Capture_Push 安装脚本（内置Python环境，无需系统Python）

[Setup]
AppName=Capture_Push
AppVersion=0.1.1
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
UninstallDisplayIcon={app}\TrayApp.exe

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Files]
; 环境安装器（PyInstaller 打包的独立 exe）- 使用低压缩级别避免内存溢出
Source: "dist\Capture_Push_Installer.exe"; DestDir: "{app}"; Flags: ignoreversion solidbreak

; Python脚本和配置
Source: "core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs
Source: "gui\*"; DestDir: "{app}\gui"; Flags: ignoreversion recursesubdirs

; 配置文件 - 同时释放到程序目录和 AppData 目录
Source: "config.ini"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.ini"; DestDir: "{localappdata}\Capture_Push"; Flags: ignoreversion

; 配置生成脚本
Source: "generate_config.py"; DestDir: "{app}"; Flags: ignoreversion

; C++托盘程序（需要预先编译）
Source: "tray\build\Release\TrayApp.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; 创建 AppData 目录
Name: "{localappdata}\Capture_Push"

[Icons]
Name: "{group}\Capture_Push托盘"; Filename: "{app}\TrayApp.exe"
Name: "{group}\配置工具"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\gui\gui.py"""
Name: "{group}\查看配置信息"; Filename: "{app}\install_config.txt"
Name: "{group}\卸载Capture_Push"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Capture_Push"; Filename: "{app}\TrayApp.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"
Name: autostart; Description: "开机自动启动托盘程序"; GroupDescription: "附加选项:"

[Registry]
; 注册安装路径
Root: HKLM; Subkey: "SOFTWARE\Capture_Push"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue

; 自启动托盘程序（如果用户选择了autostart任务）
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Capture_Push_Tray"; ValueData: """{app}\TrayApp.exe"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; 运行环境安装器（命令行模式，自动检测地区并选择镜像）
Filename: "{app}\Capture_Push_Installer.exe"; Parameters: """{app}"""; StatusMsg: "正在配置Python环境..."; Flags: waituntilterminated

; 生成配置文件
Filename: "{app}\.venv\Scripts\python.exe"; Parameters: """{app}\generate_config.py"" ""{app}"""; StatusMsg: "正在生成配置信息..."; Flags: runhidden waituntilterminated

; 安装后选项
Filename: "{app}\TrayApp.exe"; Description: "启动 Capture_Push 托盘程序"; Flags: nowait postinstall skipifsilent
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
// 初始化安装
function InitializeSetup(): Boolean;
begin
  Result := True;
  
  // 显示欢迎信息
  MsgBox('Capture_Push 安装程序' + #13#10 + #13#10 + 
         '✓ 内置Python环境：已就绪' + #13#10 +
         '✓ 安装大小：约 1200 MB' + #13#10 +
         '✓ 无需系统Python' + #13#10 + #13#10 + 
         '点击“下一步”继续安装', 
         mbInformation, MB_OK);
end;

// 安装完成后的处理
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // 这里可以添加额外的安装后处理
  end;
end;

// 卸载前的清理
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // 停止可能正在运行的托盘程序
    if MsgBox('检测到托盘程序可能正在运行，是否尝试关闭？', mbConfirmation, MB_YESNO) = IDYES then
    begin
      // 这里可以添加关闭程序的代码
    end;
  end;
end;
