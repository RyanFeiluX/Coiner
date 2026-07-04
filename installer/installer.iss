#define MyAppName "Coiner"
#define MyAppPublisher "Coiner"
#define MyAppURL "https://github.com/Coiner/Coiner"
#define MyAppExeName "main.exe"

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#ifndef StageDir
  #define StageDir "build-installer"
#endif

[Setup]
AppId={{B4F1E8A3-2C5D-4A7E-9D6F-1E8B3A2C5D4A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile={#StageDir}\LICENSE
PrivilegesRequired=admin
OutputDir=output
OutputBaseFilename=Coiner-Setup-{#MyAppVersion}
Compression=lzma2/ultra
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile={#StageDir}\resource\public\vite.svg
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#StageDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\resource\*"; DestDir: "{app}\resource"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageDir}\ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageDir}\magick.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageDir}\config.example.toml"; DestDir: "{app}"; DestName: "config.toml"; Flags: ignoreversion onlyifdoesntexist
Source: "{#StageDir}\start.bat"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\storage"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: shellexec postinstall skipifsilent nowait; WorkingDir: "{app}"

[Code]
function InitializeSetup: Boolean;
begin
  Result := True;
end;
