; AppId must remain stable for every future version to upgrade in place.
#ifndef AppVersion
  #error Pass /DAppVersion=<version> to ISCC, or use build_installer.py
#endif
#define AppGuid "{AD9693D4-F584-4A15-8E39-9242E3C657D2}"

[Setup]
AppId={{#AppGuid}
AppName=PhoneDrive
AppVersion={#AppVersion}
AppPublisher=DistantMyth
AppPublisherURL=https://github.com/DistantMyth/PhoneDrive
AppSupportURL=https://github.com/DistantMyth/PhoneDrive/issues
AppUpdatesURL=https://github.com/DistantMyth/PhoneDrive/releases/latest
DefaultDirName={localappdata}\Programs\PhoneDrive
DefaultGroupName=PhoneDrive
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
UsePreviousTasks=yes
UninstallDisplayIcon={app}\PhoneDrive.exe
AppMutex=Local\PhoneDrive.Desktop
CloseApplications=yes
RestartApplications=no
OutputDir=dist
OutputBaseFilename=PhoneDrive-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
VersionInfoVersion={#AppVersion}

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "dist\PhoneDrive\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PhoneDrive"; Filename: "{app}\PhoneDrive.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\PhoneDrive"; Filename: "{app}\PhoneDrive.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\PhoneDrive.exe"; Description: "Launch PhoneDrive"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  InstalledVersion: String;
  InstalledPacked, NewPacked: Int64;
begin
  Result := True;
  if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppGuid}_is1', 'DisplayVersion', InstalledVersion) then
    if StrToVersion(InstalledVersion, InstalledPacked) and StrToVersion('{#AppVersion}', NewPacked) then
      if ComparePackedVersion(InstalledPacked, NewPacked) > 0 then
      begin
        SuppressibleMsgBox('A newer version of PhoneDrive is already installed. Uninstall it first if you want to downgrade.', mbError, MB_OK, IDOK);
        Result := False;
      end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  StartupCommand: String;
begin
  if CurUninstallStep = usPostUninstall then
    if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'PhoneDrive', StartupCommand) then
      if Pos('"' + ExpandConstant('{app}\PhoneDrive.exe') + '"', StartupCommand) = 1 then
        RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'PhoneDrive');
  { Saved devices and credentials in AppData are deliberately retained. }
end;
