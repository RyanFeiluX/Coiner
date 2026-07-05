param(
    [switch]$SkipVue,
    [switch]$SkipPyInstaller,
    [switch]$SkipStage,
    [switch]$SkipCompile
)

$batArgs = @()
if ($SkipVue) { $batArgs += "-SkipVue" }
if ($SkipPyInstaller) { $batArgs += "-SkipPyInstaller" }
if ($SkipStage) { $batArgs += "-SkipStage" }
if ($SkipCompile) { $batArgs += "-SkipCompile" }

$batPath = Join-Path $PSScriptRoot "build-installer.bat"
Write-Host "Executing: $batPath $($batArgs -join ' ')" -ForegroundColor Cyan

$proc = Start-Process -Wait -NoNewWindow -FilePath $batPath -ArgumentList $batArgs -PassThru
exit $proc.ExitCode
