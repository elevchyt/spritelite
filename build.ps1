param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$distExe = Join-Path $projectRoot "dist\SpriteLite.exe"
Set-Location $projectRoot

function Get-PythonLauncher {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-m")
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python", "-m")
    }

    throw "Python was not found on PATH. Install Python or activate your virtual environment first."
}

if ($Clean) {
    foreach ($path in @("build", "dist", "SpriteLite.spec")) {
        if (Test-Path $path) {
            Remove-Item $path -Recurse -Force
        }
    }
}

$pythonLauncher = Get-PythonLauncher

Write-Host "Installing build dependencies..." -ForegroundColor Cyan
& $pythonLauncher[0] $pythonLauncher[1] pip install -r requirements.txt pyinstaller

Write-Host "Building SpriteLite.exe..." -ForegroundColor Cyan
& $pythonLauncher[0] $pythonLauncher[1] PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name SpriteLite `
    --icon icon.ico `
    --add-data "icons;icons" `
    --add-data "icon.ico;." `
    main.py

if (-not (Test-Path $distExe)) {
    throw "Build finished but the executable was not found at $distExe"
}

Write-Host "Build complete: $distExe" -ForegroundColor Green