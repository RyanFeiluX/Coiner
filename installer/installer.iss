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
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#StageDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\resource\*"; DestDir: "{app}\resource"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\config.toml"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "{#StageDir}\start.bat"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\storage"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: shellexec postinstall skipifsilent nowait; WorkingDir: "{app}"

[CustomMessages]
DependenciesTitle=External Dependencies
DependenciesDescription=Additional software required by Coiner
DependenciesText=Coiner requires FFmpeg and ImageMagick to function properly.%n%n1. FFmpeg (required for video processing)%n   Download from: https://www.gyan.dev/ffmpeg/builds/%n   Or install via: winget install FFmpeg%n%n2. ImageMagick (required for text/subtitle rendering)%n   Download from: https://imagemagick.org/archive/binaries/%n   Or install via: winget install ImageMagick%n%nAfter installing ImageMagick on Windows,%nset imagemagick_path in config.toml to the magick.exe path.%n%nNote: imageio-ffmpeg (bundled) can auto-download FFmpeg if not found.%nYou may skip FFmpeg and let it be downloaded automatically.

[Code]
var
  DependenciesPage: TOutputMsgWizardPage;

procedure InitializeWizard;
begin
  DependenciesPage := CreateOutputMsgPage(
    wpInfoAfter,
    CustomMessage('DependenciesTitle'),
    CustomMessage('DependenciesDescription'),
    CustomMessage('DependenciesText')
  );
end;
