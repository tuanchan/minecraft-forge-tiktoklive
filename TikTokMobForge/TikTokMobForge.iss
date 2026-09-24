#ifndef PublishDir
  #define PublishDir "artifacts\desktop"
#endif
#define AppVersion "1.1.2"
[Setup]
AppId={{BA5F109F-5188-41E9-A897-12B5A39C879F}
AppName=TikTok Mob Forge
AppVersion={#AppVersion}
AppPublisher=TikTok Mob Forge
DefaultDirName={localappdata}\Programs\TikTokMobForge
DefaultGroupName=TikTok Mob Forge
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=artifacts\installer
OutputBaseFilename=TikTokMobForge-Setup-{#AppVersion}
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll,*.pyd
RestartApplications=no
UninstallDisplayIcon={app}\TikTokMobForge.Desktop.exe
SetupLogging=yes
SetupIconFile=Desktop\iconapp.ico
[Tasks]
Name: desktopicon; Description: "Tạo lối tắt trên Desktop"; Flags: unchecked
[Files]
Source: "{#PublishDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\TikTok Mob Forge"; Filename: "{app}\TikTokMobForge.Desktop.exe"
Name: "{autodesktop}\TikTok Mob Forge"; Filename: "{app}\TikTokMobForge.Desktop.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\TikTokMobForge.Desktop.exe"; Description: "Mở TikTok Mob Forge"; Flags: nowait postinstall skipifsilent
[Code]
function HasWebView2: Boolean;
var Version: String;
begin
  Result := RegQueryStringValue(HKLM32, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version);
  if not Result then
    Result := RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version);
  Result := Result and (Version <> '') and (Version <> '0.0.0.0');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var ExitCode: Integer;
begin
  Result := '';
  ExtractTemporaryFile('stop_installed_runtime.ps1');
  if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + ExpandConstant('{tmp}\stop_installed_runtime.ps1') + '" -InstallRoot "' + ExpandConstant('{app}') + '"',
    '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then begin
    Result := 'Không thể đóng dịch vụ nền TikTok Mob. Đóng ứng dụng rồi thử lại.';
    Exit;
  end;
  if ExitCode <> 0 then begin
    Result := 'TikTok Mob vẫn đang chạy hoặc đang lưu. Đóng cửa sổ ứng dụng rồi thử cài lại.';
    Exit;
  end;
  if not HasWebView2 then begin
    ExtractTemporaryFile('MicrosoftEdgeWebview2Setup.exe');
    if not Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'), '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then
      Result := 'Không chạy được bộ cài Microsoft Edge WebView2 Runtime.'
    else if not HasWebView2 then
      Result := 'Cần Microsoft Edge WebView2 Runtime. Hãy kết nối Internet để cài rồi chạy lại Setup.';
  end;
end;

[Files]
Source: "artifacts\dependencies\MicrosoftEdgeWebview2Setup.exe"; Flags: dontcopy
Source: "scripts\stop_installed_runtime.ps1"; Flags: dontcopy
