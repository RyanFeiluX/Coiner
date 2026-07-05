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
#ifexist "compiler:Languages\ChineseSimplified.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#StageDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\resource\*"; DestDir: "{app}\resource"; Flags: ignoreversion recursesubdirs createallsubdirs
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
var
  DependenciesPage: TOutputMsgWizardPage;

procedure InitializeWizard;
begin
  DependenciesPage := CreateOutputMsgPage(
    wpInfoAfter,
    'External Dependencies',
    'Additional software required by Coiner',
    'Coiner requires FFmpeg and ImageMagick to function properly.' + #13#10 +
    '' + #13#10 +
    '1. FFmpeg (required for video processing)' + #13#10 +
    '   Download from: https://www.gyan.dev/ffmpeg/builds/' + #13#10 +
    '   Or install via: winget install FFmpeg' + #13#10 +
    '' + #13#10 +
    '2. ImageMagick (required for text/subtitle rendering)' + #13#10 +
    '   Download from: https://imagemagick.org/archive/binaries/' + #13#10 +
    '   Or install via: winget install ImageMagick' + #13#10 +
    '' + #13#10 +
    'After installing ImageMagick on Windows,' + #13#10 +
    'set imagemagick_path in config.toml to the magick.exe path.' + #13#10 +
    '' + #13#10 +
    'Note: imageio-ffmpeg (bundled) can auto-download FFmpeg if not found.' + #13#10 +
    'You may skip FFmpeg and let it be downloaded automatically.'
  );
end;
